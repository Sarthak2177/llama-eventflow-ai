import json
from typing import Optional, List
from langchain_core.tools import tool

# We will inject the MCP session into these functions later, or we can use a global context
mcp_session = None

from . import mcp_client
from . import broker_client

def set_mcp_session(session):
    global mcp_session
    mcp_session = session



@tool
async def search_solace_entity(entity_type: str, name: str = None, domain_name: str = None, entity_id: str = None):
    """Lists all entities of a given type, or finds a specific entity. ALWAYS use this (with domain_name) to find entities like applications, events, event_apis, or event_api_products inside a specific Domain!
    entity_type: domain, application, event, event_api, event_api_product, schema, enum
    """
    if not mcp_session: return "Error: mcp_session not set"
    res = await mcp_client._search_entity(mcp_session, entity_type, name, domain_name, entity_id)
    return json.dumps(res)

@tool
async def get_entity_relationships(entity_id: str, relationship_type: str):
    """Fetches complex related objects across entity types (e.g. events produced by an app).
    DO NOT use this to find entities inside a domain; use search_solace_entity with domain_name instead!
    relationship_type MUST be one of: applications, produced_events, consumed_events, event_apis, event_api_products (finds products containing an event/api), consuming_applications
    """
    if not mcp_session: return "Error: mcp_session not set"
    res = await mcp_client._get_relationships(mcp_session, entity_id, relationship_type)
    return json.dumps(res)

@tool
async def duplicate_solace_entity(entity_type: str, source_entity_id: str, new_name: str):
    """Duplicates an existing entity, copying its configuration and relationships to a new entity.
    entity_type: application, event, event_api, event_api_product
    """
    if not mcp_session: return "Error: mcp_session not set"
    res = await mcp_client._duplicate_entity(mcp_session, entity_type, source_entity_id, new_name)
    return json.dumps(res)

@tool
async def update_entity_relationship(entity_type: str, version_id: str, action: str, target_type: str, target_version_id: str):
    """Updates the relationships of a specific version of an entity (e.g., adding an event to an event API).
    action: add, remove
    """
    if not mcp_session: return "Error: mcp_session not set"
    res = await mcp_client._update_relationship(mcp_session, entity_type, version_id, action, target_type, target_version_id)
    return json.dumps(res)

@tool
async def get_entity_impact(entity_type: str, version_id: str):
    """Finds out what other entities rely on or reference a given entity version (reverse dependency lookup).
    entity_type: event, schema, event_api
    """
    # Note: get_entity_impact doesn't seem fully implemented in mcp_client.py, I'll route it to get_relationships for now.
    if not mcp_session: return "Error: mcp_session not set"
    if entity_type == "event":
        res = await mcp_client._get_relationships(mcp_session, version_id, "consuming_applications")
        return json.dumps(res)
    return json.dumps({"error": "Impact lookup not fully implemented for this type."})

@tool
async def get_schema_content(entity_id: str):
    """Smart tool that retrieves the actual JSON or AVRO schema data fields. You can pass an Event ID, Event Version ID, Schema ID, or Schema Version ID."""
    if not mcp_session: return "Error: mcp_session not set"
    res = await mcp_client._get_schema_content(mcp_session, entity_id)
    return json.dumps(res)

@tool
async def get_event_topic(event_id: str):
    """Fetches the exact topic string (delivery address) for a given Event. ALWAYS use this before subscribing a queue to an event!"""
    if not mcp_session: return "Error: mcp_session not set"
    res = await mcp_client._call_mcp(mcp_session, "getEventVersions", {"eventIds": [event_id]})
    if not res: return json.dumps({"error": "Event versions not found."})
    
    try:
        levels = res[0].get("deliveryDescriptor", {}).get("address", {}).get("addressLevels", [])
        topic = "/".join([lvl["name"] if lvl["addressLevelType"] == "literal" else "*" for lvl in levels])
        return json.dumps({"event_id": event_id, "topic_string": topic})
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
async def create_solace_entity(entity_type: str, name: str, domain_name: str = None, enum_values: List[str] = None):
    """Creates a new Solace Domain, Application, or Event, along with its initial version (0.1.0)."""
    if not mcp_session: return "Error: mcp_session not set"
    res = await mcp_client._create_entity(mcp_session, entity_type, name, domain_name, enum_values)
    return json.dumps(res)

@tool
async def create_solace_entity_version(entity_type: str, entity_id: str, version: str, enum_values: List[str] = None):
    """Creates a new version for an existing Application, Event, Event API, or Event API Product."""
    if not mcp_session: return "Error: mcp_session not set"
    res = await mcp_client._create_version(mcp_session, entity_type, entity_id, version, enum_values)
    return json.dumps(res)

@tool
async def delete_solace_entity(entity_type: str, entity_id: str):
    """Deletes a specific Solace Domain, Application, Event, Event API, or Event API Product."""
    if not mcp_session: return "Error: mcp_session not set"
    res = await mcp_client._delete_entity(mcp_session, entity_type, entity_id)
    return json.dumps(res)

@tool
async def delete_solace_entity_version(entity_type: str, version_id: str):
    """Deletes a specific version of a Solace Application, Event, Event API, or Event API Product."""
    if not mcp_session: return "Error: mcp_session not set"
    res = await mcp_client._delete_version(mcp_session, entity_type, version_id)
    return json.dumps(res)

# Broker Tools
@tool
async def manage_solace_queue(action: str, queue_name: str, new_queue_name: str = None, max_ttl: int = None, max_msg_spool_usage: int = None):
    """Get, create, update, delete, or duplicate a queue on the Solace event broker.
    action: get, create, update, delete, duplicate
    """
    args = {"action": action, "queue_name": queue_name, "new_queue_name": new_queue_name, "max_ttl": max_ttl, "max_msg_spool_usage": max_msg_spool_usage}
    res = await broker_client.execute_broker_tool("manage_solace_queue", args)
    return res

@tool
async def get_queue_stats(queue_name: str):
    """Read-only tool to fetch live telemetry for a queue, including message counts, spool usage, and currently bound consumers/clients."""
    res = await broker_client.execute_broker_tool("get_queue_stats", {"queue_name": queue_name})
    return res

@tool
async def list_queues():
    """Read-only tool to list all queues on the broker along with their basic telemetry."""
    res = await broker_client.execute_broker_tool("list_queues", {})
    return res

@tool
async def get_queue_subscriptions(queue_name: str):
    """Read-only tool to list all topic subscriptions configured on a specific queue."""
    res = await broker_client.execute_broker_tool("get_queue_subscriptions", {"queue_name": queue_name})
    return res

@tool
async def manage_queue_subscription(action: str, queue_name: str, topic: str = None):
    """List, add, or remove topic subscriptions on a specific queue.
    action: list, add, remove
    """
    args = {"action": action, "queue_name": queue_name, "topic": topic}
    res = await broker_client.execute_broker_tool("manage_queue_subscription", args)
    return res

@tool
async def get_client_username(client_username: str):
    """Read-only tool to fetch the configuration of a client username."""
    res = await broker_client.execute_broker_tool("get_client_username", {"client_username": client_username})
    return res

ALL_TOOLS = [
    search_solace_entity, get_entity_relationships, duplicate_solace_entity,
    update_entity_relationship, get_entity_impact, get_schema_content,
    create_solace_entity, create_solace_entity_version, delete_solace_entity,
    delete_solace_entity_version, manage_solace_queue, get_queue_stats,
    list_queues, get_queue_subscriptions, manage_queue_subscription,
    get_client_username, get_event_topic
]
