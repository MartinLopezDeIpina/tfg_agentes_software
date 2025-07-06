import asyncio
from dataclasses import dataclass, field
from importlib import resources
from typing import List, Dict, Any, Optional, TypeVar, Generic, DefaultDict
from abc import ABC, abstractmethod
import asyncio
import time
from collections import defaultdict
from sqlalchemy.orm import Session

import os

from src.utils.utils import get_file_text, get_start_to_end_lines_from_text_code
from src.db.db_utils import get_chunk_code

from src.db.db_connection import DBConnection
from src.utils.proyect_tree import generate_repo_tree_str
from src.code_indexer.llm_tools import AsyncLLMPrompter, AsyncEmbedder
from src.code_indexer.prompt_builder import DocPromptBuilder
from src.code_indexer.extra_docs_generator import generate_extra_docs, get_extra_docs_if_exists

from db.models import FileChunk, FSEntry

"""
Patrón Pipeline de forma asíncrona con sistema integrado de logging.

Se define un Pipeline que recorre los ficheros y chunks de forma asíncrona. En cada uno se quiere realizar una serie de 
procesos (stages) que se pueden añadir al pipeline.

Se han definido 3 stages: 
- ContextPreparationStage: Prepara el contexto del pipeline, ficheros y chunks.
- DocumentationGeneratorStage: Genera la documentación para cada chunk.
- EmbeddingIndexingStage: Genera el índice de embeddings para cada chunk.
"""

# Definición de tipos para el pipeline
T = TypeVar('T')
U = TypeVar('U')

@dataclass
class StageProgress:
    """Clase para seguimiento de progreso de una etapa específica"""
    total_processed: int = 0
    total_time: float = 0.0

@dataclass
class PipelineContext:
    """Contexto global del pipeline"""
    repo_path: str
    extra_docs_path: str
    db_session: Session
    files_to_ignore: List[str]
    repo_tree_str: str
    files: List['FileContext'] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)

    # Logging y seguimiento de progreso
    log_frequency: int = 10  # Cada cuántos chunks se muestra un log
    stage_progress: Dict[str, Dict[str, StageProgress]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(StageProgress))
    )
    start_time: float = field(default_factory=time.time)

    def log_stage_completion(self, stage_name: str, stage_type: str, chunk_id: Optional[str] = None,
                             elapsed: float = 0.0):
        """Registra la finalización de una etapa y muestra progreso periódico"""
        progress = self.stage_progress[stage_type][stage_name]

        # Actualizar estadísticas
        progress.total_processed += 1
        progress.total_time = elapsed

        # Decidir si mostrar un log basado en la frecuencia configurada
        if progress.total_processed % self.log_frequency == 0:
            self._show_progress_log(stage_name, stage_type)

    def _show_progress_log(self, stage_name: str, stage_type: str):
        """Muestra un log con el progreso actual"""
        progress = self.stage_progress[stage_type][stage_name]
        total_chunks = self.stats.get('total_chunks', 0)

        if total_chunks > 0:
            percentage = (progress.total_processed / total_chunks) * 100
            elapsed_time = time.time() - self.start_time

            print(f"[{stage_type.upper()}] {stage_name}: {progress.total_processed}/{total_chunks} "
                  f"chunks ({percentage:.1f}%), tiempo transcurrido: {elapsed_time:.3f}")

    def log_pipeline_status(self):
        """Muestra un resumen del estado de todas las etapas del pipeline"""
        print("\n=== ESTADO DEL PIPELINE ===")
        total_elapsed = time.time() - self.start_time

        print(f"Tiempo total transcurrido: {total_elapsed:.1f}s")
        print(f"Ficheros procesados: {len(self.files)}/{self.stats.get('total_files', 0)}")

        for stage_type, stages in self.stage_progress.items():
            print(f"\n[{stage_type.upper()}]")
            for stage_name, progress in stages.items():
                total = self.stats.get('total_chunks', 0)
                if total > 0:
                    percentage = (progress.total_processed / total) * 100
                    print(f"  - {stage_name}: {progress.total_processed}/{total} ({percentage:.1f}%), "
                          f"tiempo: {progress.total_time:.1f}s")
        print("===========================\n")


@dataclass
class FileContext:
    """Contexto para un fichero con todos sus chunks"""
    file: FSEntry
    pipeline_context: PipelineContext
    file_code: str
    file_extra_docs: str = ""
    chunks: List['ChunkContext'] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)

    @property
    def file_path(self) -> str:
        return self.file.path

    @property
    def repo_path(self) -> str:
        return self.pipeline_context.repo_path


@dataclass
class ChunkContext:
    """Contexto para un chunk específico, referenciando su FileContext padre"""
    chunk: FileChunk
    file_context: FileContext
    chunk_code: str
    referenced_chunks_path_and_code: List[tuple] = field(default_factory=list)
    referencing_chunks_path_and_code: List[tuple] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)

    @property
    def file_path(self) -> str:
        return self.file_context.file_path

    @property
    def file_code(self) -> str:
        return self.file_context.file_code

    @property
    def file_extra_docs(self) -> str:
        return self.file_context.file_extra_docs

    @property
    def is_only_chunk_in_file(self) -> bool:
        return len(self.file_context.chunks) == 1

    @property
    def pipeline_context(self) -> PipelineContext:
        return self.file_context.pipeline_context

    @property
    def chunk_id(self) -> str:
        return f"{self.file_path}:{self.chunk.start_line}-{self.chunk.end_line}"


class PipelineStage(Generic[T, U], ABC):
    """Clase base abstracta para las etapas del pipeline"""

    @abstractmethod
    async def process(self, data: T) -> U:
        """Procesa los datos de entrada y retorna el resultado"""
        pass

    @property
    def name(self) -> str:
        return self.__class__.__name__


class ChunkPipelineStage(PipelineStage[ChunkContext, ChunkContext]):
    """Base para etapas que procesan chunks individuales"""
    pass


class FilePipelineStage(PipelineStage[FileContext, FileContext]):
    """Base para etapas que procesan ficheros completos"""
    pass


class PipelinePipelineStage(PipelineStage[PipelineContext, PipelineContext]):
    """Base para etapas que procesan el contexto completo del pipeline"""
    pass


class Pipeline:
    """Clase principal del pipeline que orquesta la ejecución de las etapas"""

    def __init__(self, log_frequency: int = 10):
        self.chunk_stages: List[ChunkPipelineStage] = []
        self.file_stages: List[FilePipelineStage] = []
        self.pipeline_stages: List[PipelinePipelineStage] = []
        self.log_frequency = log_frequency

    def add_chunk_stage(self, stage: ChunkPipelineStage) -> 'Pipeline':
        """Añade una etapa que procesa chunks"""
        self.chunk_stages.append(stage)
        return self

    def add_file_stage(self, stage: FilePipelineStage) -> 'Pipeline':
        """Añade una etapa que procesa ficheros"""
        self.file_stages.append(stage)
        return self

    def add_pipeline_stage(self, stage: PipelinePipelineStage) -> 'Pipeline':
        """Añade una etapa que procesa el contexto completo"""
        self.pipeline_stages.append(stage)
        return self

    async def execute(self, context: PipelineContext) -> PipelineContext:
        """Ejecuta el pipeline completo"""
        # Configurar logging
        context.log_frequency = self.log_frequency
        context.start_time = time.time()

        # Etapas a nivel de pipeline
        for stage in self.pipeline_stages:
            context = await stage.process(context)

        # Etapas a nivel de fichero
        for file_context in context.files:
            for stage in self.file_stages:
                file_context = await stage.process(file_context)

        # Etapas a nivel de chunk
        chunk_tasks = []
        for file_context in context.files:
            for chunk_context in file_context.chunks:
                task = self._process_chunk(chunk_context, self.chunk_stages)
                chunk_tasks.append(task)

        if chunk_tasks:
            # Mostrar estado inicial
            print(f"Iniciando procesamiento paralelo de {len(chunk_tasks)} chunks...")

            # Ejecutar todas las tareas en paralelo
            await asyncio.gather(*chunk_tasks)

            # Mostrar resumen final
            context.log_pipeline_status()

        total_time = time.time() - context.start_time
        print(f"Pipeline completado en {total_time:.2f} segundos.")
        return context

    async def _process_chunk(self, chunk_context: ChunkContext, stages: List[ChunkPipelineStage]):
        """Procesa un chunk a través de todas sus etapas, con logging integrado"""
        pipeline_context = chunk_context.pipeline_context

        for stage in stages:
            stage_start = time.time()
            chunk_id = chunk_context.chunk_id

            # Procesar el chunk
            chunk_context = await stage.process(chunk_context)

            # Registrar finalización
            elapsed = time.time() - stage_start
            pipeline_context.log_stage_completion(stage.name, "chunk", chunk_id, elapsed)

        return chunk_context


class ContextPreparationStage(PipelinePipelineStage):
    """Etapa que prepara los contextos para todos los ficheros y chunks"""

    def prepare_chunk_context(self, context: FileContext):
        for chunk in context.file.chunks:
            chunk_code = get_start_to_end_lines_from_text_code(
                context.file_code, chunk.start_line, chunk.end_line
            )

            # Obtener chunks referenciados
            referenced_chunks = []
            for ref_chunk in chunk.referenced_chunks:
                ref_chunk_path = ref_chunk.file.path
                ref_chunk_code = get_chunk_code(context.pipeline_context.db_session, ref_chunk, context.repo_path)
                referenced_chunks.append((ref_chunk_path, ref_chunk_code))

            # Obtener chunks que referencian a este
            referencing_chunks = []
            for ref_chunk in chunk.referencing_chunks:
                ref_chunk_path = ref_chunk.file.path
                ref_chunk_code = get_chunk_code(context.pipeline_context.db_session, ref_chunk, context.repo_path)
                referencing_chunks.append((ref_chunk_path, ref_chunk_code))

            # Crear contexto de chunk con referencia a su fichero padre
            chunk_context = ChunkContext(
                chunk=chunk,
                file_context=context,
                chunk_code=chunk_code,
                referenced_chunks_path_and_code=referenced_chunks,
                referencing_chunks_path_and_code=referencing_chunks
            )

            # Añadir el chunk al fichero
            context.chunks.append(chunk_context)

    def prepare_file_and_chunk_context(self, context: PipelineContext):

        files_query = context.db_session.query(FSEntry).filter(
            FSEntry.is_directory == False,
            ~FSEntry.path.in_(context.files_to_ignore)
        )

        for file in files_query.all():

            file_path = file.path
            file_absolute_path = os.path.join(context.repo_path, file_path)

            try:

                file_code = get_file_text(file_absolute_path)
                if file_code == "":
                    continue
                file_extra_docs = get_extra_docs_if_exists(file_path, context.extra_docs_path)

                file_context = FileContext(
                    file=file,
                    pipeline_context=context,
                    file_code=file_code,
                    file_extra_docs=file_extra_docs
                )

                self.prepare_chunk_context(file_context)
                context.files.append(file_context)

            except Exception as e:
                print(f"Error al procesar el fichero {file_absolute_path}: {e}")

    async def prepare_pipeline_context(self, context: PipelineContext):
        """
        Genera el mapa del repositorio y la documentación extra
        """
        # Generar el mapa del repositorio
        context.repo_tree_str = generate_repo_tree_str(context.repo_path)

        # Generar la documentación extra
        context.extra_docs_path = resources.files("servidor_mcp_bd_codigo").joinpath(
            "src",
            "code_indexer",
            "extra_docs"
        )
        extra_doc_exist = len(os.listdir(context.extra_docs_path)) > 0
        if not extra_doc_exist:
            generate_extra_docs(
                repo_path=context.repo_path,
                files_to_ignore=context.files_to_ignore,
                extra_docs_path=context.extra_docs_path
            )

    async def process(self, context: PipelineContext) -> PipelineContext:
        """
        Inicia los contextos de pipeline, fichero y chunk.
        """

        await self.prepare_pipeline_context(context)
        self.prepare_file_and_chunk_context(context)

        context.stats['total_files'] = len(context.files)
        context.stats['total_chunks'] = sum(len(file_context.chunks) for file_context in context.files)
        print(f"Contexto preparado: {context.stats['total_files']} ficheros y {context.stats['total_chunks']} chunks.")

        return context

class DocumentationGeneratorStage(ChunkPipelineStage):
    """Etapa que genera documentación para un chunk"""

    def __init__(self, llm_prompter, prompt_builder):
        self.llm_prompter = llm_prompter
        self.prompt_builder = prompt_builder

    async def process(self, chunk_context: ChunkContext) -> ChunkContext:
        # Crear el prompt para la documentación
        self.prompt_builder.restart_prompt()

        # Ahora usamos las propiedades para acceder a la información sin duplicidad
        self.prompt_builder.add_prompt_chunk_code(chunk_context.chunk_code, chunk_context.file_path)
        self.prompt_builder.add_prompt_file_code(
            chunk_context.file_code,
            chunk_context.is_only_chunk_in_file,
            chunk_context.chunk.start_line,
            chunk_context.chunk.end_line
        )
        self.prompt_builder.add_prompt_extra_docs(chunk_context.file_extra_docs)
        self.prompt_builder.add_prompt_repo_map(chunk_context.pipeline_context.repo_tree_str)
        self.prompt_builder.add_prompt_referenced_chunks(chunk_context.referenced_chunks_path_and_code)
        self.prompt_builder.add_prompt_referencing_chunks(chunk_context.referencing_chunks_path_and_code)

        chunk_doc_prompt = self.prompt_builder.build_prompt()
        chunk_doc_response = await self.llm_prompter.async_execute_prompt(chunk_doc_prompt)
        chunk_doc = chunk_doc_response.content

        # Guardar el resultado en el chunk y en el contexto
        chunk_context.chunk.docs = chunk_doc
        chunk_context.results['documentation'] = chunk_doc

        return chunk_context

class EmbeddingIndexingStage(ChunkPipelineStage):
    """Etapa que genera un índice de embeddings para los chunks desde la documentación generada"""
    llm_embedder: AsyncEmbedder

    def __init__(self):
        self.llm_embedder = AsyncEmbedder()

    async def process(self, context: ChunkContext) -> ChunkContext:
        doc_to_index = context.results.get('documentation', None)
        if doc_to_index:
            embedding_index = await self.llm_embedder.async_embed_document(doc_to_index)
            context.results['embedding_index'] = embedding_index

            context.chunk.embedding = embedding_index

        return context


async def run_documentation_pipeline(repo_path, files_to_ignore=None, log_frequency=10):

    if files_to_ignore is None:
        files_to_ignore = []

    db_session = DBConnection.get_session()

    context = PipelineContext(
        repo_path=repo_path,
        db_session=db_session,
        files_to_ignore=files_to_ignore,
        repo_tree_str="",
        extra_docs_path="",
        log_frequency=log_frequency
    )

    llm_prompter = AsyncLLMPrompter()
    prompt_builder = DocPromptBuilder()

    pipeline = Pipeline(log_frequency=log_frequency)

    # Añadir etapas
    pipeline.add_pipeline_stage(ContextPreparationStage())
    pipeline.add_chunk_stage(DocumentationGeneratorStage(llm_prompter, prompt_builder))
    pipeline.add_chunk_stage(EmbeddingIndexingStage())

    result_context = await pipeline.execute(context)

    db_session.commit()

    print(f"Pipeline completado. Documentados {result_context.stats['total_files']} ficheros y {result_context.stats['total_chunks']} chunks.")

    return result_context

def run_documentation_pipeline_sync(repo_path, files_to_ignore=None, log_frequency=2):
    return asyncio.run(run_documentation_pipeline(repo_path, files_to_ignore, log_frequency))