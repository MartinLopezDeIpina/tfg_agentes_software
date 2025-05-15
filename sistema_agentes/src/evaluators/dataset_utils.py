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

