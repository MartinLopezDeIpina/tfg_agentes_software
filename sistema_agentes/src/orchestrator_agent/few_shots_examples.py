from langchain_core.prompts import PromptTemplate, FewShotPromptTemplate


examples = [
    {
      "question": "Task related to the project's general information",
      "answer": "Call only agents with access the required information documentation"
    },
    {
      "question": "Task related to specific project information",
      "answer": "Call only agents with access to documentation containing that information and agents with access to sources related to that information"
    },
    {
      "question": "Task related to the project's architecture",
      "answer": "Call only agents with documentation about the software architecture and agents with access to the project's source code"
    },
    {
      "question": "Task related to a specific data source of the project such as source code or specific documentation",
      "answer": "Call only the agent responsable to that data source or documentation"
    }
]

example_prompt = PromptTemplate.from_template("Question: {question}\n{answer}")

few_shots_template = FewShotPromptTemplate(
    examples=examples,
    example_prompt=example_prompt,
    input_variables=[],
    suffix="",
    prefix="Here are some abstract examples of some type of questions you need to answer:"
)
orchestrator_few_shots = few_shots_template.format()




