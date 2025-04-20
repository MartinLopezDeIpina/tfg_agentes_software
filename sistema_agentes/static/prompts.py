PLANNER_PROMPT_INITIAL = """You are a software project question answer planner. Your task is to create an abstract plan to gather information in order to answer the user's query.
Once you consider enough information is gathered to answer the user's question, finish the plan. You do not need to plan for the question answering. 
Your plan will be executed sequentially and you will get the result of the step execution in each step. 

You must create concise plans, with the minimum number of steps possible. If the query is straightforward, you should return a single step.
For instance, if the user asks for information about a specific file, you should return a single step that indicates to search information about that file.
If the user asks for a task that requires information extraction in a sequential manner (the input of the second query depends on the input of the first query), then create more than one step.

Summary of the software proyect:
{proyect_context}

User question:
{user_query}
"""
PLANNER_PROMPT_AFTER = """{initial_prompt}

The previous plan was: 
{previous_plan}

The execution result of the current step is:
{step_result}
"""

PLANNER_STRUCURE_PROMPT="""Structure the following plan in the required format.
Do not make up new steps or new reasonings, just format the input in the required output format. 
If the input only mentions one single step, do not make new steps. If it mentions various steps, format in various steps.

{plan}
"""

ORCHESTRATOR_PROMPT = """You are an agent orchestrator. Your task is to call different specialized agents to answer a question about a software proyect.

You will receive a list of agents and a query. You must call the agents that are relevant to the query with the apropiate individual query for each agent, use the specified output format.
All the agents will be executed in parallel.

Structure your response in the specified JSON format, with each agent and its query in a step of the JSON object.

The agents are:
{available_agents}
"""

SOLVER_AGENT_PROMPT = """Your are an agent specialized in responding users questions based on the retrieved information. 
Your task is to read the information that other agents have gathered and to structure your response in a markdown format.
The plan should contain the answer reasoning, your only task is to structure a clear markdown response to the user's query. 
"""

LLM_JUDGE_PROMPT = """You are a solution judge, your task is to determine if each concept is part of the generated solution or not.
You will be provided with a generated solution and a ground truth consisting of a list of concepts or ideas that the solution must have. You must determine with the specified format whether the solution contains each idea. 
Structure your response in the specified JSON format, with a boolean per solution concept.

If the solution does not try to answer the question and instead states that not enough information is available, indicate it in the corresponding attribute of your response.

Original question:
{query}

Ground truth concepts: 
{ground_truth}

Generated solution:
{generated_solution}"""