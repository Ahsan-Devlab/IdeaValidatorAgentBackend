from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.llm import build_llm
from app.models import StructuredIdea


parser = PydanticOutputParser(pydantic_object=StructuredIdea)


prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a startup analyst. Extract structured fields from the user's idea. "
     "Use only what the user said. Do not invent facts. "
     "product_type must be saas, web_app, mobile_app, or other. "
     "target_customer: describe the customer WITHOUT the place; put the place in region. "
     "keywords: 3 to 5 search phrases of 2-4 words, what a person would type to find "
     "existing apps for this problem, most specific first (example: 'udhaar app'). Never single words.\n\n"
     "{format_instructions}"),
    ("human", "{idea}"),
]).partial(format_instructions=parser.get_format_instructions())

#The .partial() method in LangChain lets you pre-fill a subset of variables in a prompt template, 
# returning a new template that only requires the remaining variables.

chain = prompt | build_llm(temperature=0) | parser

def run_intake(idea: str) -> StructuredIdea:
    """
    Run the intake chain to extract structured fields from the user's idea.

    Args:
        idea (str): The user's idea to be evaluated.

    Returns:
        StructuredIdea: The structured representation of the idea.
    """
    return chain.invoke({"idea": idea})