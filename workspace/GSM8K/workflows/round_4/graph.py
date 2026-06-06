from typing import Literal
import workspace.GSM8K.workflows.template.operator as operator
import workspace.GSM8K.workflows.round_4.prompt as prompt_custom
from scripts.async_llm import create_llm_instance
import weave


DatasetType = Literal["HumanEval", "MBPP", "GSM8K", "MATH", "HotpotQA", "DROP"]

class Workflow:
    def __init__(
        self,
        name: str,
        llm_config,
        dataset: DatasetType,
    ) -> None:
        self.name = name
        self.dataset = dataset
        self.llm = create_llm_instance(llm_config)
        self.sc_ensemble = operator.ScEnsemble(self.llm)
        self.custom = operator.Custom(self.llm)
        self.programmer= operator.Programmer(self.llm)

    @weave.op()
    async def __call__(self, problem: str):
        """
        Implementation of the workflow
        Each operator is callable, you can call it directly.
        """
        # Custom solver step
        custom_solution = await self.custom(input=prompt_custom.SIMPLE_SOLVER_1 + problem, instruction="", role="simple_solver_1")

        # Programmer step 1
        programmer_solution_1 = await self.programmer(problem=problem, analysis=prompt_custom.PROGRAMMER_1)

        # Programmer step 2
        programmer_solution_2 = await self.programmer(problem=problem, analysis=prompt_custom.PROGRAMMER_2)

        # ScEnsemble step
        final_solution = await self.sc_ensemble(solutions=[custom_solution['response'], programmer_solution_1['output'], programmer_solution_2['output']], problem=problem)

        # Refine answer step
        refined_answer = await self.custom(input=prompt_custom.REFINE_ANSWER_PROMPT + f"Problem: {problem}, Solutions: {final_solution['response']}", instruction="", role="refine_answer_1")

        return refined_answer['response'], self.llm.get_usage_summary()["total_cost"]
