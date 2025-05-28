#!/usr/bin/env python3
"""
Analizador de resultados de experimentos LangSmith
Calcula el promedio de llm-as-a-judge y el total de tokens
"""

import pandas as pd
import sys
import os
from pathlib import Path

def analyze_langsmith_results(csv_path):
    """
    Analiza un archivo CSV de resultados de LangSmith
    
    Args:
        csv_path (str): Ruta al archivo CSV
        
    Returns:
        dict: Diccionario con los resultados del análisis
    """
    
    # Verificar que el archivo existe
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"El archivo {csv_path} no existe")
    
    # Leer el CSV
    try:
        df = pd.read_csv(csv_path)
        print(f"✅ Archivo leído correctamente: {len(df)} filas encontradas")
    except Exception as e:
        raise Exception(f"Error al leer el archivo CSV: {e}")
    
    # Verificar que las columnas necesarias existen
    required_columns = ['llm-as-a-judge', 'tokens']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        print(f"⚠️  Columnas faltantes: {missing_columns}")
        print(f"📋 Columnas disponibles: {list(df.columns)}")
    
    results = {}
    
    # Calcular promedio de llm-as-a-judge
    if 'llm-as-a-judge' in df.columns:
        # Convertir a numérico, los valores no numéricos se convierten a NaN
        llm_judge_values = pd.to_numeric(df['llm-as-a-judge'], errors='coerce')
        
        # Filtrar valores no nulos
        valid_llm_judge = llm_judge_values.dropna()
        
        if len(valid_llm_judge) > 0:
            llm_judge_avg = valid_llm_judge.mean()
            results['llm_judge_promedio'] = llm_judge_avg
            results['llm_judge_count'] = len(valid_llm_judge)
        else:
            results['llm_judge_promedio'] = None
            results['llm_judge_count'] = 0
            print("⚠️  No se encontraron valores válidos en 'llm-as-a-judge'")
    else:
        results['llm_judge_promedio'] = None
        results['llm_judge_count'] = 0
    
    # Calcular total de tokens
    if 'tokens' in df.columns:
        # Convertir a numérico, los valores no numéricos se convierten a NaN
        token_values = pd.to_numeric(df['tokens'], errors='coerce')
        
        # Filtrar valores no nulos y sumar
        valid_tokens = token_values.dropna()
        
        if len(valid_tokens) > 0:
            total_tokens = valid_tokens.sum()
            results['tokens_total'] = int(total_tokens)  # Convertir a entero
            results['tokens_count'] = len(valid_tokens)
        else:
            results['tokens_total'] = 0
            results['tokens_count'] = 0
            print("⚠️  No se encontraron valores válidos en 'tokens'")
    else:
        results['tokens_total'] = 0
        results['tokens_count'] = 0
    
    # Información adicional
    results['total_rows'] = len(df)
    results['successful_runs'] = len(df[df['status'] == 'success']) if 'status' in df.columns else None
    
    return results

def print_results(results):
    """Imprime los resultados de forma formateada"""
    
    print("\n" + "="*50)
    print("📊 RESULTADOS DEL ANÁLISIS")
    print("="*50)
    
    print(f"📈 Total de evaluaciones: {results['total_rows']}")
    
    if results['successful_runs'] is not None:
        success_rate = (results['successful_runs'] / results['total_rows']) * 100
        print(f"✅ Evaluaciones exitosas: {results['successful_runs']} ({success_rate:.1f}%)")
    
    print(f"\n🎯 LLM-as-a-Judge:")
    if results['llm_judge_promedio'] is not None:
        print(f"   Promedio: {results['llm_judge_promedio']:.4f}")
        print(f"   Valores válidos: {results['llm_judge_count']}")
    else:
        print("   No hay datos válidos disponibles")
    
    print(f"\n🔢 Tokens Total:")
    print(f"   Total tokens: {results['tokens_total']:,}")
    print(f"   Valores válidos: {results['tokens_count']}")
    
    print("="*50)

def main():
    """Función principal"""
    
    if len(sys.argv) != 2:
        print("Uso: python script.py <ruta_del_csv>")
        print("Ejemplo: python script.py resultados_langsmith.csv")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    
    try:
        # Analizar el archivo
        results = analyze_langsmith_results(csv_path)
        
        # Mostrar resultados
        print_results(results)
        
        # Guardar resumen en archivo de texto
        output_file = Path(csv_path).stem + "_resumen.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("RESUMEN DE ANÁLISIS LANGSMITH\n")
            f.write("="*40 + "\n\n")
            f.write(f"Archivo analizado: {csv_path}\n")
            f.write(f"Total evaluaciones: {results['total_rows']}\n")
            f.write(f"Evaluaciones exitosas: {results['successful_runs']}\n\n")
            f.write(f"LLM-as-a-Judge promedio: {results['llm_judge_promedio']}\n")
            f.write(f"Valores válidos LLM Judge: {results['llm_judge_count']}\n\n")
            f.write(f"Total tokens: {results['tokens_total']:,}\n")
            f.write(f"Valores válidos tokens: {results['tokens_count']}\n")
        
        print(f"\n💾 Resumen guardado en: {output_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
