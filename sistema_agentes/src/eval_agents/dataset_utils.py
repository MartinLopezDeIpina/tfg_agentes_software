import os
from typing import List

import pandas as pd
from langsmith import Client

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


def create_agent_dataset(langsmith_client: Client, agent: str, agent_df: DataFrame, agent_column: str, query_column: str, messages_column: str, plan_column: str):
    dataset_name = get_dataset_name_for_agent(agent)
    dataset = create_or_empty_langsmith_dataset(langsmith_client, dataset_name)

    """
    Inputs son la columna query, messages y current plan si estos existen.
    Outputs son todas las demás columnas que no son la del nombre del agente.
    """
    examples = []
    for _, row in agent_df.iterrows():
        inputs = {"query": row[query_column], "messages": row[messages_column], "current_plan": row[plan_column]}

        outputs = {}
        for col in agent_df.columns:
            if col != agent_column and col != query_column:
                outputs[col] = row[col]

        examples.append({"inputs": inputs, "outputs": outputs})

    # Crear ejemplos en LangSmith
    try:
        langsmith_client.create_examples(
            inputs=[example["inputs"] for example in examples],
            outputs=[example["outputs"] for example in examples],
            dataset_id=dataset.id
        )
    except Exception as e:
        print(f"❌ Error al crear ejemplos para '{agent}': {e}")

def create_langsmith_datasets(dataset_prueba: bool = False):
    langsmith_client = Client()

    agent_column = 'agent'
    query_column = 'query'
    messages_column = 'messages'
    plan_column = 'current_plan'
    df = None
    try:
        df = get_dataset_csv_df([agent_column, query_column], dataset_prueba)
    except Exception as e:
        print(f"Error procesando csv: {e}")

    unique_agents = df[agent_column].unique()
    for agent in tqdm(unique_agents, desc="Creando datasets", unit="dataset"):
        agent_df = df[df[agent_column] == agent]
        if len(agent_df) == 0:
            print(f"⚠️ Advertencia: No hay filas para el agente '{agent}', saltando...")
            continue
        if dataset_prueba:
            agent = f"{agent}_prueba"
        create_agent_dataset(langsmith_client, agent, agent_df, agent_column, query_column, messages_column, plan_column)
