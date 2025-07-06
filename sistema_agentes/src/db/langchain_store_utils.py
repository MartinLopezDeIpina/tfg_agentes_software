import ast
import asyncio
import json
import uuid
from collections import defaultdict
from typing import Sequence, List, Dict, Any, Tuple

import numpy as np
from langchain_core.messages import SystemMessage, AIMessage
from langgraph.store.base import PutOp
from langgraph.store.postgres import AsyncPostgresStore
from langgraph_sdk.schema import SearchItem
from matplotlib import pyplot as plt
from scipy.spatial.distance import cdist
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE

from config import STORE_COLLECTION_PREFIX, default_llm
from src.db.postgres_connection_manager import PostgresPoolManager
from src.utils import get_list_string_with_indexes
from static.prompts import MEMORY_CLUSTER_SUMMARIZER_PROMPT


async def save_agent_memory_in_store(store: AsyncPostgresStore, values: dict, agent_name: str, key:str):
    await store.aput(
        namespace=(STORE_COLLECTION_PREFIX, agent_name),
        key=key,
        value=values
    )

async def increment_counter(store: AsyncPostgresStore, item: SearchItem):
    if "access_count" in item.value:
        item.value["access_count"] += 1

    try:
        await save_agent_memory_in_store(
            store=store,
            values=item.value,
            agent_name=item.namespace[1],
            key=item.key
        )
    except Exception as e:
        print(f"Error guardando memoria en store: {e}")


async def increment_memory_docs_counter(store: AsyncPostgresStore, memory_docs: List[SearchItem]):
    tasks = [increment_counter(store=store, item=item) for item in memory_docs]
    await asyncio.gather(*tasks)

async def hybrid_memory_similarity_counter_search(store: AsyncPostgresStore, agent_name: str, query: str, k_docs: int = 5, similarity_weight: float = 0.75, counter_weight: float = 0.25):
    memory_docs = await store.asearch((STORE_COLLECTION_PREFIX, agent_name), query=query, limit=k_docs * 2)
    if not memory_docs:
        return []

    # Normalizar los contadores en una escala del 0-1
    max_counter = max([doc.value.get("access_count", 0) for doc in memory_docs], default=1)

    # Crear una lista de tuplas (documento, score_híbrido)
    scored_docs = []
    for doc in memory_docs:
        similarity_score = doc.score or 0

        access_counter = doc.value.get("access_count", 0)
        normalized_counter = access_counter / max_counter if max_counter > 0 else 0

        hybrid_score = (
                similarity_weight * similarity_score +
                counter_weight * normalized_counter
        )

        scored_docs.append((doc, hybrid_score))

    scored_docs.sort(key=lambda x: x[1], reverse=True)

    return [doc for doc, _ in scored_docs[:k_docs]]

async def count_agent_memory_documents(agent_name: str) -> int:
    """
    Realiza una operación COUNT directamente en la tabla SQL que representa al store, filtrando por el prefijo de la colección.
    """
    postgres_pool_manager = await PostgresPoolManager.get_instance()
    async with postgres_pool_manager.get_connection() as connection:
        async with connection.cursor() as cursor:
            collection_prefix = f"{STORE_COLLECTION_PREFIX}.{agent_name}"

            await cursor.execute(
                """
                SELECT COUNT(*) 
                FROM store 
                WHERE prefix = %s
                """,
                (collection_prefix,)
            )

            count = (await cursor.fetchone())[0]
            return count


async def fetch_store_items_with_embeddings(agent_name: str,limit: int = 10000) -> List[Dict[str, Any]]:
    try:
        prefix = f"{STORE_COLLECTION_PREFIX}.{agent_name}"
        pool_manager = await PostgresPoolManager.get_instance()
        async with pool_manager.get_connection() as conn:
            async with conn.cursor() as cur:
                # Consulta SQL con JOIN entre las tablas store y store_vectors
                query = """
                   SELECT s.key, s.value, sv.embedding
                   FROM store s
                   LEFT JOIN store_vectors sv ON s.key = sv.key
                   WHERE s.prefix = %s
                   LIMIT %s
                   """

                await cur.execute(query, (prefix, limit))
                rows = await cur.fetchall()
                column_names = [desc[0] for desc in cur.description]
            results = []
            for row in rows:
                row_dict = dict(zip(column_names, row))
                results.append(row_dict)

            return results

    except Exception as e:
        print(f"Error buscando items en store {prefix}: {e}")
        return []


def visualize_clusters(vectors, labels, agent_name):
    # Reducir dimensionalidad para visualización con t-SNE
    tsne = TSNE(n_components=2, random_state=42, perplexity=5)
    reduced_data = tsne.fit_transform(vectors)

    # Configuración de estilo global
    plt.rcParams.update({
        'font.size': 38,  # Aumentado de 14 a 18
        'axes.labelsize': 32,  # Etiquetas de ejes especialmente grandes
        'xtick.labelsize': 22,
        'ytick.labelsize':22
    })

    # Crear gráfico de dispersión con tamaño de figura ajustado
    plt.figure(figsize=(10, 8))

    # Aumentar tamaño de los puntos (s=150 en vez del valor por defecto ~20-30)
    scatter = plt.scatter(reduced_data[:, 0], reduced_data[:, 1],
                          c=labels, cmap='viridis', s=150, alpha=0.8)

    plt.xlabel('Dimensión 1', fontsize=24)
    plt.ylabel('Dimensión 2', fontsize=24)

    # Ajustar márgenes para evitar recortes
    plt.tight_layout(pad=3.0)

    # Añadir cuadrícula para mejor referencia visual
    plt.grid(True, linestyle='--', alpha=0.3)

    plt.show()


def print_elbow_graph(K, distortions, optimal_k, elbow_idx, adjusted_idx):
    plt.rcParams.update({
        'axes.labelsize': 32,
        'xtick.labelsize': 22,
        'ytick.labelsize': 22,
        'font.size': 14
        })

    plt.figure(figsize=(12, 6))

    plt.plot(K, distortions, 'bo-', linewidth=6, markersize=20)

    # Etiquetas con mayor tamaño
    plt.xlabel('Número de clusters (k)', fontsize=24)
    plt.ylabel('Suma de distancias cuadráticas', fontsize=24)

    # Líneas de referencia más gruesas
    # Marcar el punto óptimo
    plt.axvline(x=optimal_k, color='r', linestyle='--', linewidth=5,
                label=f'k óptimo = {optimal_k}')


    # Leyenda más grande y con borde para destacar
    plt.legend(fontsize=24, frameon=True, facecolor='white', edgecolor='gray')

    # Cuadrícula mejorada
    plt.grid(True, linestyle='--', alpha=0.7)

    # Ajustar márgenes
    plt.tight_layout(pad=3.0)

    plt.show()

def find_optimal_clusters_elbow(data, max_k=25, min_k = 2, separation_factor=0, visualize_elbow=True):
    max_k = min(max_k, len(data))
    K = range(min_k, max_k + 1)

    distortions = []
    for k in K:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(data)
        # Calcular la distorsión (suma de distancias cuadráticas)
        distortions.append(sum(np.min(cdist(
            data, kmeans.cluster_centers_, 'euclidean'
        ) ** 2, axis=1)) / data.shape[0])

    # Usar la segunda derivada para encontrar el punto de máxima curvatura -> número de clusters óptimo
    deltas = np.gradient(np.gradient(distortions))
    elbow_idx = np.argmax(deltas)

    # Deslizar el codo según el factor de separación -> ¿queremos más clusters que el óptimo matemático?
    adjusted_idx = int(elbow_idx + (len(K) - 1 - elbow_idx) * separation_factor)
    optimal_k = K[min(max(0, adjusted_idx), len(K) - 1)]

    if visualize_elbow:
        print_elbow_graph(K, distortions, optimal_k, elbow_idx, adjusted_idx)

    # Aplicar K-means con el número óptimo de clusters
    optimal_kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
    optimal_kmeans.fit(data)

    return optimal_kmeans

async def group_memory_clusters(agent_name: str, visualize=True) -> defaultdict[Any, List]:
    try:
        embeddings_items = await fetch_store_items_with_embeddings(agent_name=agent_name, limit=10000)
        # De string a floats y de floats a arrays de numpy -> shape (num_docs, len_embedding)
        vectors = np.array([np.array(ast.literal_eval(item["embedding"])) for item in embeddings_items])

        # Aplicar KMeans clustering buscando la cantidad de clusters óptima con el método del codo
        kmeans = find_optimal_clusters_elbow(vectors)
        labels = kmeans.labels_

        # Agrupar los resultados por clusters desde los labels
        clusters = defaultdict(list)
        for i, label in enumerate(labels):
            clusters[label].append(embeddings_items[i])

        # 6. Visualizar clusters
        if visualize:
            visualize_clusters(vectors, labels, agent_name)

        return clusters
    except Exception as e:
        print(f"Error creando clusters de memoria: {e}")
        return defaultdict(list)

async def create_and_put_cluster_memories_in_store(store: AsyncPostgresStore, clustered_memories: defaultdict[Any, List], agent_name: str):
    summarizer_llm = default_llm
    inputs = []
    # Lista de listas que contienen las citas únicas
    grouped_cites = []
    
    for value in clustered_memories.values():
        if len(value) == 1:
            continue

        memories_content = [memory_value["value"]["concept"] for memory_value in value]
        memories_str = get_list_string_with_indexes(memories_content)
        input = [
            SystemMessage(
                content=MEMORY_CLUSTER_SUMMARIZER_PROMPT.format(
                    memories=memories_str
                )
            )
        ]
        inputs.append(input)

        # Quedarse con la lista de citas sin repetidos, distinguiendo por su url
        unique_cites_dict = {}
        for memory in value:
            for cite in memory["value"]["cites"]:
                unique_cites_dict[json.loads(cite)["data"].get("doc_url")] = cite
        unique_cites_list = list(unique_cites_dict.values())
        grouped_cites.append(unique_cites_list)

    results = await summarizer_llm.abatch(inputs=inputs)

    # Añadir todos los clusters comprimidos asíncronamente
    put_opeartions = [
        (
            PutOp(
                namespace=(STORE_COLLECTION_PREFIX, agent_name),
                key=str(uuid.uuid4()),
                value={
                    "concept": result.content,
                    "cites": grouped_cites[i]
                }
            )
        )
        for i, result in enumerate(results)
    ]
    await store.abatch(put_opeartions)

async def delete_cluster_memories(store: AsyncPostgresStore, clustered_memories: [Any, List], agent_name: str):
    delete_ops = []
    namespace = (STORE_COLLECTION_PREFIX, agent_name)
    for cluster_memories in clustered_memories.values():
        if len(cluster_memories) > 1:
            delete_ops.extend([
                store.adelete(namespace=namespace, key=cluster_memory["key"])
                for cluster_memory in cluster_memories
            ])
    await asyncio.gather(*delete_ops)

async def get_and_manage_agent_memory_docs(store: AsyncPostgresStore, agent_name: str, query: str, k_docs: int = 5, similarity_weight: float = 0.75, counter_weight: float = 0.25, cluster_threshold: int = 10) -> List[SearchItem]:
    """
    Obtiene k elementos de memoria relevantes para la consulta.
    Incrementa el access_count de todos en uno
    En caso de sobrepasar el límite de memorias en el store, iniciar el proceso de agrupación.
    """
    memory_docs = await hybrid_memory_similarity_counter_search(store, agent_name, query, k_docs, similarity_weight, counter_weight)
    await increment_memory_docs_counter(store, memory_docs)

    agent_memory_count = await count_agent_memory_documents(agent_name=agent_name)
    if agent_memory_count > cluster_threshold:
        print(f"Agrupando memoria de agente {agent_name}...")
        clustered_memories = await group_memory_clusters(agent_name)
        # Si no se consigue crear correctamente los resúmenes entonces no eliminar las memorias
        try:
            await create_and_put_cluster_memories_in_store(store=store, clustered_memories=clustered_memories, agent_name=agent_name)
            await delete_cluster_memories(store=store, clustered_memories=clustered_memories, agent_name=agent_name)
        except Exception as e:
            print(f"Error ejecutando summarizer de memorias: {e}")

    return memory_docs

async def delete_all_memory_documents(store: AsyncPostgresStore):
    deleted_count = 0

    namespaces = await store.alist_namespaces()

    # Para cada namespace, buscar todos los elementos y eliminarlos
    for namespace in namespaces:
        items = await store.asearch(namespace)

        # Eliminar cada elemento encontrado
        delete_ops = []
        for item in items:
            # Crear una operación de eliminación para cada documento
            delete_ops.append(PutOp(namespace=item.namespace, key=item.key, value=None))
            deleted_count += 1

        # Ejecutar las operaciones de eliminación en batch si hay elementos
        if delete_ops:
            await store.abatch(delete_ops)

    print(f"Se han eliminado {deleted_count} documentos")
    return deleted_count




