"""LLM utility module"""

from os import environ as env
import base64
from io import BytesIO

import requests

from langchain_openai import (
    ChatOpenAI,
    OpenAIEmbeddings,
    AzureChatOpenAI,
    AzureOpenAIEmbeddings,
)

# from langchain_huggingface import HuggingFaceEmbeddings

from gjdanawa_uploader.core.utils import SINGLETON_MANAGER
from gjdanawa_uploader.configs import CFG_LLM


LLM_KEY = "llm"
EMBEDDINGS_KEY = "embeddings"


############################################################
# Chat LLM
############################################################
def get_llm(
    openai_api_key: str | None = None,
    configs_chat_openai: dict = CFG_LLM.chat_openai,
):
    """Get llm instance"""
    key = (openai_api_key, LLM_KEY)
    if not SINGLETON_MANAGER.has_instance(key):
        if openai_api_key == "azure":
            llm = get_azure_chat_openai(configs_chat_openai)
        elif openai_api_key:
            llm = get_chat_openai(openai_api_key, configs_chat_openai)
        else:
            raise ValueError(f"Invalid openai_api_key: {openai_api_key}")

        # Validate openai_api_key
        llm.invoke("")
        SINGLETON_MANAGER.set_instance(key, llm)
    return SINGLETON_MANAGER.get_instance(key)


def get_chat_openai(
    openai_api_key: str | None = None, configs_chat_openai: dict = CFG_LLM.chat_openai
) -> ChatOpenAI:
    """Get ChatOpenAI instance"""
    if openai_api_key is None:
        openai_api_key = env["OPENAI_API_KEY"]
    return ChatOpenAI(
        openai_api_key=openai_api_key,
        model=configs_chat_openai.model,
        temperature=configs_chat_openai.temperature,
    )


def get_azure_chat_openai(
    configs_chat_openai: dict = CFG_LLM.chat_openai,
) -> AzureChatOpenAI:
    """Get AzureChatOpenAI instance"""
    return AzureChatOpenAI(
        # azure_endpoint=env["AZURE_OPENAI_ENDPOINT"],
        deployment_name=env["AZURE_OPENAI_LLM_DEPLOYMENT_NAME"],
        # openai_api_version=env["AZURE_OPENAI_API_VERSION"],
        # openai_api_key=env["AZURE_OPENAI_API_KEY"],
        model=env["AZURE_OPENAI_LLM_MODEL"],
        temperature=configs_chat_openai.temperature,
    )


############################################################
# Embeddings
############################################################
def get_embeddings(
    openai_api_key: str | None = None, configs_emb: dict = CFG_LLM.openai_embeddings
):
    """Get embeddings instance"""
    key = (openai_api_key, EMBEDDINGS_KEY)
    if not SINGLETON_MANAGER.has_instance(key):
        if openai_api_key == "azure":
            emb = get_azure_embeddings(configs_emb)
        elif openai_api_key is None:
            emb = get_openai_embeddings(configs_emb)
        else:
            raise ValueError(f"Invalid openai_api_key: {openai_api_key}")

        # Validate openai_api_key
        emb.embed_query("")
        SINGLETON_MANAGER.set_instance(key, emb)
    return SINGLETON_MANAGER.get_instance(key)


def get_openai_embeddings(
    configs_emb: dict = CFG_LLM.openai_embeddings,
) -> OpenAIEmbeddings:
    """Get OpenAIEmbeddings instance"""
    return OpenAIEmbeddings(
        # openai_api_key=openai_api_key,
        model=configs_emb.model,
    )


def get_azure_embeddings(
    configs_emb: dict = CFG_LLM.openai_embeddings,
) -> AzureOpenAIEmbeddings:
    """Get AzureEmbeddings instance"""
    return AzureOpenAIEmbeddings(
        # azure_endpoint=env["AZURE_OPENAI_ENDPOINT"],
        deployment=env["AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT"],
        # openai_api_version=env["AZURE_OPENAI_API_VERSION"],
        # openai_api_key=env["AZURE_OPENAI_API_KEY"],
        model=env["AZURE_OPENAI_EMBEDDINGS_MODEL"],
    )


# def get_huggingface_embeddings():
#     """Get HuggingFace instance"""
#     key = "HuggingFaceEmbeddings"
#     if not hasattr(SINGLETON_MANAGER, key):
#         embeddings = HuggingFaceEmbeddings(
#             model_name=CFGS["chain"].huggingface.embeddings_model,
#             model_kwargs={"device": "cuda"},
#         )
#         setattr(SINGLETON_MANAGER, key, embeddings)
#     return getattr(SINGLETON_MANAGER, key)


############################################################
# Image embedding
############################################################
# def get_image(image_path_or_url: str) -> Image.Image:
#     """Get image from local path or URL"""
#     if image_path_or_url.startswith(("http://", "https://")):
#         response = requests.get(image_path_or_url)
#         response.raise_for_status()
#         return Image.open(BytesIO(response.content))
#     return Image.open(image_path_or_url)


# def embed_image(url: str) -> list[float]:
#     """Embed images

#     - https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/how-to/image-retrieval?tabs=csharp#call-the-vectorize-image-api
#     - https://community.openai.com/t/get-embeddings-for-images/524241/5?u=alchemine
#     - https://huggingface.co/blog/image-similarity
#     - https://medium.com/@jeremy-k/unlocking-openai-clip-part-2-image-similarity-bf0224ab5bb0
#     """
#     # Azure Computer Vision API 설정
#     endpoint = env[
#         "AZURE_OPENAI_ENDPOINT"
#     ]  # "<endpoint>"  # 여기에 실제 엔드포인트를 입력하세요
#     subscription_key = env[
#         "AZURE_OPENAI_API_KEY"
#     ]  # "<subscription-key>"  # 여기에 실제 구독 키를 입력하세요

#     # API URL
#     url = f"{endpoint}/computervision/retrieval:vectorizeImage?api-version=2024-02-01&model-version=2023-04-15"

#     # 헤더 설정
#     headers = {
#         "Content-Type": "application/json",
#         "Ocp-Apim-Subscription-Key": subscription_key,
#     }

#     # 요청 본문 (payload)
#     payload = {
#         "url": "https://learn.microsoft.com/azure/ai-services/computer-vision/media/quickstarts/presentation.png"
#     }

#     # POST 요청 보내기
#     response = requests.post(url, headers=headers, json=payload)

#     # 응답 확인
#     if response.status_code == 200:
#         result = response.json()
#         print("Image vector:", result["vector"])
#     else:
#         print(f"Error: {response.status_code}")
#         print(response.text)


############################################################
# Trace chain
############################################################
def trace_chain():
    env["LANGCHAIN_TRACING_V2"] = "true"
    env["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    # os.environ["LANGCHAIN_ENDPOINT"] = "<your-api-key>"


############################################################
# Constants
############################################################
CHAT_LLM = get_llm("azure")
EMBEDDINGS = get_embeddings("azure")
