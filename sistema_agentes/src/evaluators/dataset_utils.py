import json
from datasets import load_dataset
import os
from typing import List

import pandas as pd
from langsmith import Client
from langsmith.schemas import ExampleCreate

from pandas import DataFrame
from tqdm import tqdm

from config import REPO_ROOT_ABSOLUTE_PATH, CSV_DATASET_RELATIVE_PATH, CSV_DATASET_PRUEBA_RELATIVE_PATH


def get_dataset_name_for_agent(agent_name: str):
    return f"evaluate_{agent_name}"

def get_dataset_csv_df(required_columns: List["str"], is_prueba: bool):
    if is_prueba:
        dataset_relative_path = CSV_DATASET_PRUEBA_RELATIVE_PATH
    else:
        dataset_relative_path = CSV_DATASET_RELATIVE_PATH
    csv_dataset_path = os.path.join(REPO_ROOT_ABSOLUTE_PATH, "sistema_agentes", dataset_relative_path)
    if not os.path.exists(csv_dataset_path):
        print(f"Error, csv dataset not found in path: {csv_dataset_path}")

    df = pd.read_csv(csv_dataset_path)
    
    for column in required_columns:
        if column not in df.columns:
            error = f"❌ Error: No se encontró la columna '{column}' en el CSV"
            raise Exception(error)
            
    return df

def search_langsmith_dataset(langsmith_client: Client, dataset_name: str = None, agent_name: str = None):
    if dataset_name is None:
        if agent_name:
            dataset_name = get_dataset_name_for_agent(agent_name)
        else:
            return None

    if langsmith_client.has_dataset(dataset_name=dataset_name):
        dataset = langsmith_client.read_dataset(dataset_name=dataset_name)
        return dataset
    else:
        return None

def create_or_empty_langsmith_dataset(langsmith_client: Client, dataset_name: str):
    """
    Si el dataset existe lo vacía.
    Si el dataset no existe crea uno vacío.
    """
    dataset = search_langsmith_dataset(langsmith_client = langsmith_client, dataset_name = dataset_name)
    if dataset:
        langsmith_client.delete_dataset(dataset_id=dataset.id)

    dataset = langsmith_client.create_dataset(
        dataset_name=dataset_name,
        description=f"Dataset {dataset_name} creado correctamente"
    )
    return dataset


def create_agent_dataset(langsmith_client: Client, agent: str, agent_df: DataFrame, input_columns: List[str]):
    dataset_name = get_dataset_name_for_agent(agent)
    dataset = create_or_empty_langsmith_dataset(langsmith_client, dataset_name)

    """
    Inputs son la columna query, messages, current_plan y difficulty si estos existen.
    Outputs son todas las demás columnas que no son la del nombre del agente.
    """
    inputs_list = []
    outputs_list = []

    output_columns = [col for col in agent_df.columns if col not in input_columns]

    for _, row in agent_df.iterrows():
        inputs = {col: row[col] for col in input_columns}
        outputs = {col: row[col] for col in output_columns}

        inputs_list.append(inputs)
        outputs_list.append(outputs)

    try:
        langsmith_client.create_examples(
            inputs=inputs_list,
            outputs=outputs_list,
            dataset_id=dataset.id
        )
        print(f"✅ Dataset '{dataset_name}' creado con {len(inputs_list)} ejemplos")
    except Exception as e:
        print(f"❌ Error al crear ejemplos para '{agent}': {e}")

def create_langsmith_datasets(dataset_prueba: bool = False, agents_to_update: List[str] = None):
    langsmith_client = Client()

    agent_column = "agent"
    query_column = "query"
    input_column_names = [agent_column, query_column, "messages", "current_plan"]

    df = None
    try:
        df = get_dataset_csv_df([agent_column, query_column], dataset_prueba)
    except Exception as e:
        print(f"Error procesando csv: {e}")

    unique_agents = df[agent_column].unique()
    if agents_to_update:
        unique_agents = [agent for agent in unique_agents if agent in agents_to_update]

    for agent in tqdm(unique_agents, desc="Creando datasets", unit="dataset"):
        agent_df = df[df[agent_column] == agent]

        if len(agent_df) == 0:
            print(f"⚠️ Advertencia: No hay filas para el agente '{agent}', saltando...")
            continue

        if dataset_prueba:
            agent = f"{agent}_prueba"
        create_agent_dataset(langsmith_client, agent, agent_df, input_column_names)

def create_main_agent_memory_partitioned_datasets(split_train_proportion: float = 0.8):
    num_train_per_one_test = int(1 / (1 - split_train_proportion))

    langsmith_client = Client()
    dataset_name = "evaluate_main_agent_memory"

    dataset = search_langsmith_dataset(langsmith_client = langsmith_client, dataset_name = "evaluate_main_agent")
    if not dataset:
        print(f"Error dividiendo particiones")
        return

    memory_dataset = create_or_empty_langsmith_dataset(langsmith_client=langsmith_client, dataset_name=dataset_name)
    examples = langsmith_client.list_examples(dataset_id=dataset.id)
    new_examples = []
    for i, example in enumerate(examples):
        if i % num_train_per_one_test == 0:
            split = "test"
        else:
            split = "train"

        new_example = ExampleCreate(
            inputs=example.inputs,
            outputs=example.outputs,
            metadata=example.metadata,
            split=split
        )
        new_examples.append(new_example)

    langsmith_client.create_examples(
        dataset_id=memory_dataset.id,
        examples=new_examples
    )
    print(f"Dataset {dataset_name} creado correctamente")

def create_easy_and_hard_datasets():
    import pandas as pd
    import json

    evaluations_location = f"{REPO_ROOT_ABSOLUTE_PATH}/sistema_agentes/src/evaluators/eval_results/main_agent"
    complex_system_result_df = pd.read_csv(f"{evaluations_location}/planificador_orquestador.csv")
    simple_system_result_df = pd.read_csv(f"{evaluations_location}/orquestador_react.csv")

    complex_system_result_df.set_index('id', inplace=True)
    simple_system_result_df.set_index('id', inplace=True)

    # Función para extraer solo la query del campo inputs (formato JSON)
    def extract_query(inputs_json):
        try:
            inputs_dict = json.loads(inputs_json)
            return inputs_dict.get('query', '')
        except:
            return ''

    complex_system_result_df['query'] = complex_system_result_df['inputs'].apply(extract_query)
    simple_system_result_df['query'] = simple_system_result_df['inputs'].apply(extract_query)

    ejemplos_dificiles = []
    ejemplos_faciles = []

    common_ids = set(complex_system_result_df.index) & set(simple_system_result_df.index)

    for ejemplo_id in common_ids:
        score_complex = complex_system_result_df.loc[ejemplo_id, 'llm-as-a-judge']
        score_simple = simple_system_result_df.loc[ejemplo_id, 'llm-as-a-judge']
        query = complex_system_result_df.loc[ejemplo_id, 'query']

        # Nuevo criterio: es difícil si el complejo es mejor que el simple
        # O si cualquiera de los dos sistemas tiene precisión < 0.5
        if score_complex > score_simple or score_simple < 0.5 or score_complex < 0.5:
            ejemplos_dificiles.append({
                'id': ejemplo_id,
                'query': query
            })
        else:  # solo será fácil si el simple es igual o mejor que el complejo Y ambos tienen precisión >= 0.5
            ejemplos_faciles.append({
                'id': ejemplo_id,
                'query': query
            })

    df_dificiles = pd.DataFrame(ejemplos_dificiles)
    df_faciles = pd.DataFrame(ejemplos_faciles)

    df_dificiles.to_csv(f"{evaluations_location}/ejemplos_dificiles.csv", index=False)
    df_faciles.to_csv(f"{evaluations_location}/ejemplos_faciles.csv", index=False)

    print(f"Ejemplos difíciles encontrados: {len(ejemplos_dificiles)}")
    print(f"Ejemplos fáciles encontrados: {len(ejemplos_faciles)}")

def create_question_classifier_dataset():
        hf_dataset_name="MartinElMolon/tfg_clasificador"
        langsmith_client = Client()
        dataset_name = "evaluate_classifier_agent"
        dataset = create_or_empty_langsmith_dataset(langsmith_client=langsmith_client, dataset_name=dataset_name)

        try:
            hf_dataset = load_dataset(hf_dataset_name)
            df = pd.DataFrame(hf_dataset["test"])

            new_examples = []
            for _, row in df.iterrows():
                new_example = ExampleCreate(
                    inputs={"query": row["question"]},
                    outputs={
                        "class": str.upper(row["class"])
                    }
                )
                new_examples.append(new_example)

            langsmith_client.create_examples(
                dataset_id=dataset.id,
                examples=new_examples
            )

            print(f"✅ Dataset '{dataset_name}' created with {len(new_examples)} examples")
        except Exception as e:
            print(f"❌ Error creating question classifier dataset: {e}")