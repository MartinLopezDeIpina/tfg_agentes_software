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

react_orchestrator_examples = [
    {
        "question": "Task about gathering general information",
        "answer": "Call a few agents that can provide useful information"
    },
    {
        "question": "Task about gathering information about a specific concept of the project",
        "answer": "Call only the agent that has access to that concept's information. Evaluate if further information is required."
    },
    {
        "question": "Task that requires to search information about a topic that first requires to gather information about another topic",
        "answer": "Call only the agent that has access to the first topic. After receiving the response, dynamically decide if the other call is necessary"
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
react_orchestrator_few_shots_template = FewShotPromptTemplate(
    examples=react_orchestrator_examples,
    example_prompt=example_prompt,
    input_variables=[],
    suffix="",
    prefix="Here are some abstract examples of some type of questions you need to answer:"
)
orchestrator_few_shots = few_shots_template.format()
react_orchestrator_few_shots = few_shots_template.format()



