from langchain_core.prompts import PromptTemplate, FewShotPromptTemplate

examples = [
    {
        "current_info": "",
        "question": "How does X work?",
        "plan": "Search information about X. Not finished",
        "explanation": "Searching information about X is straightforward, there is no sequential dependencies"
    },
    {
        "current_info": "",
        "question": "How does Y work?",
        "plan": "first search information about X. Then search information about Y. Not finished",
        "explanation": "A question might require to search for multiple topics"
    },
    {
        "current_info": "How X works",
        "question": "How does X work?",
        "plan": "Enough information for X has been gathered. finished",
        "explanation": "DO NOT generate additional steps if information is already gathered"
    },
    {
        "current_info": "How X works",
        "question": "How does Y work?",
        "plan": "Search for information about Y. Not finished",
        "explanation": "There is not enough information to answer the question yet"
    },
    {
        "current_info": "",
        "question": "Provide examples of how X works",
        "plan": "Search information about how X works. Then search examples of X. Not finished",
        "explanation": "A plan step might depend on previous plan results"
    },
    {
        "current_info": "No information for X was found",
        "question": "Provide examples for X",
        "plan": "No information for X was found, stop looking. finished.",
        "explanation": "If after various attempts not information was found, indicate that not information is available and finish the plan"
    },
    {
        "current_info": "The previous plan was to find information about X and then about Y. Information about X was gathered",
        "question": "Provide information about X and Y",
        "plan": "Enough information for X and Y was gathered. Finished",
        "explanation": "Dynamically adjust your plan as you go, some steps might be unnecessary"

    },
    {
        "current_info": "The previous plan was to find information about X. Information about X was gathered",
        "question": "Provide information about X",
        "plan": "Additional information about Y is necessary in order to answer the question. Not finished.",
        "explanation": "Dynamically adjust your plan as you go, some steps might not gather enough information"
    }
]

example_prompt = PromptTemplate.from_template("\t{explanation}:\n\t\tCurrent information:{current_info}\n\t\tQuestion:{question}\n\t\tPlan:{plan}")

few_shots_template = FewShotPromptTemplate(
    examples=examples,
    example_prompt=example_prompt,
    input_variables=[],
    suffix="",
    prefix="Here are some abstract examples:"
)
planner_few_shots = few_shots_template.format()




