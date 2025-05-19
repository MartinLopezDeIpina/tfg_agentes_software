from langchain_core.prompts import PromptTemplate, FewShotPromptTemplate
examples = [
    {
        "question": "qué herramientas de testing se utilizan en el proyecto",
        "answer": "EASY"
    },
    {
        "question": "cuál es el proceso de revisión de código establecido",
        "answer": "EASY"
    },
    {
        "question": "cómo se gestionan las dependencias externas en el proyecto",
        "answer": "EASY"
    },
    {
        "question": "qué convenciones de nombrado se utilizan para las variables y funciones",
        "answer": "EASY"
    },
    {
        "question": "qué tecnologías de backend se utilizan en el proyecto",
        "answer": "EASY"
    },
    {
        "question": "quién es el responsable de mantener la integración con el servicio externo de openai",
        "answer": "HARD"
    },
    {
        "question": "cómo está implementada la lógica de rate limiting en el componente de llamadas a llms",
        "answer": "HARD"
    },
    {
        "question": "dónde puedo encontrar la documentación sobre los endpoints privados del servicio de indexación",
        "answer": "HARD"
    },
    {
        "question": "qué optimizaciones específicas se han aplicado al algoritmo de recuperación de documentos similares",
        "answer": "HARD"
    },
    {
        "question": "quién es el encargado de gestionar las claves de api para los servicios externos",
        "answer": "HARD"
    }
]

example_prompt = PromptTemplate.from_template("Question: {question}\n{answer}")

few_shots_template = FewShotPromptTemplate(
    examples=examples,
    example_prompt=example_prompt,
    input_variables=[],
    suffix="",
    prefix="Here are some examples:"
)
classifier_few_shots = few_shots_template.format()



