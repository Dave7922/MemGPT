import uuid
from typing import List
from functools import partial

from fastapi import APIRouter, Depends, Body, Query, HTTPException
from pydantic import BaseModel, Field

from memgpt.server.rest_api.interface import QueuingInterface
from memgpt.server.server import SyncServer
from memgpt.server.rest_api.auth_token import get_current_user
from memgpt.data_types import AgentState
from memgpt.models.pydantic_models import LLMConfigModel, EmbeddingConfigModel, AgentStateModel

router = APIRouter()


class ListAgentsResponse(BaseModel):
    num_agents: int = Field(..., description="The number of agents available to the user.")
    agents: List[dict] = Field(..., description="List of agent configurations.")


class CreateAgentRequest(BaseModel):
    config: dict = Field(..., description="The agent configuration object.")


class CreateAgentResponse(BaseModel):
    agent_state: AgentStateModel = Field(..., description="The state of the newly created agent.")


def setup_agents_index_router(server: SyncServer, interface: QueuingInterface):
    get_current_user_with_server = partial(get_current_user, server)

    @router.get("/agents", tags=["agents"], response_model=ListAgentsResponse)
    def list_agents(
        user_id: uuid.UUID = Depends(get_current_user_with_server),
    ):
        """
        List all agents associated with a given user.

        This endpoint retrieves a list of all agents and their configurations associated with the specified user ID.
        """
        interface.clear()
        agents_data = server.list_agents(user_id=user_id)
        return ListAgentsResponse(**agents_data)

    @router.post("/agents", tags=["agents"], response_model=CreateAgentResponse)
    def create_agent(
        request: CreateAgentRequest = Body(...),
        user_id: uuid.UUID = Depends(get_current_user_with_server),
    ):
        """
        Create a new agent with the specified configuration.
        """
        interface.clear()

        try:
            agent_state = server.create_agent(user_id=user_id, **request.config)
            llm_config = LLMConfigModel(**vars(agent_state.llm_config))
            embedding_config = EmbeddingConfigModel(**vars(agent_state.embedding_config))
            return CreateAgentResponse(
                agent_state=AgentStateModel(
                    id=agent_state.id,
                    name=agent_state.name,
                    user_id=agent_state.user_id,
                    preset=agent_state.preset,
                    persona=agent_state.persona,
                    human=agent_state.human,
                    llm_config=llm_config,
                    embedding_config=embedding_config,
                    state=agent_state.state,
                    created_at=int(agent_state.created_at.timestamp()),
                )
            )
            # return CreateAgentResponse(
            #    agent_state=AgentStateModel(
            # )
        except Exception as e:
            print(str(e))
            raise HTTPException(status_code=500, detail=str(e))

    return router
