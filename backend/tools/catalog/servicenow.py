"""
ServiceNow Tools
================
OOTB tools for ServiceNow ITSM operations.
Requires: servicenow connection
"""

import requests
from typing import Optional
from ..decorators import tool


@tool(
    name="servicenow_create_incident",
    description="Create a new incident ticket in ServiceNow",
    category="itsm",
    connection_type="servicenow",
    icon="🎫"
)
def create_incident(
    short_description: str,
    description: str = "",
    urgency: int = 3,
    impact: int = 3,
    category: str = "",
    assignment_group: str = "",
    _connection: dict = None
) -> str:
    """
    Create an incident in ServiceNow.
    
    Args:
        short_description: Brief summary of the incident (required)
        description: Detailed description of the incident
        urgency: Urgency level (1=High, 2=Medium, 3=Low)
        impact: Impact level (1=High, 2=Medium, 3=Low)
        category: Incident category
        assignment_group: Group to assign the incident to
        _connection: Injected credentials from user's saved connection
    
    Returns:
        Success message with incident number or error message
    """
    if not _connection:
        return "Error: ServiceNow connection not configured. Please set up your connection first."
    
    instance_url = _connection.get("instance_url", "").rstrip("/")
    username = _connection.get("username")
    password = _connection.get("password")
    
    if not all([instance_url, username, password]):
        return "Error: Incomplete ServiceNow credentials."
    
    payload = {
        "short_description": short_description,
        "description": description,
        "urgency": str(urgency),
        "impact": str(impact)
    }
    
    if category:
        payload["category"] = category
    if assignment_group:
        payload["assignment_group"] = assignment_group
    
    try:
        response = requests.post(
            f"{instance_url}/api/now/table/incident",
            auth=(username, password),
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=30
        )
        
        if response.ok:
            data = response.json()
            incident_number = data.get("result", {}).get("number", "Unknown")
            incident_sys_id = data.get("result", {}).get("sys_id", "")
            return f"✅ Incident {incident_number} created successfully. (ID: {incident_sys_id})"
        else:
            return f"❌ Error creating incident: {response.status_code} - {response.text}"
            
    except requests.exceptions.RequestException as e:
        return f"❌ Connection error: {str(e)}"


@tool(
    name="servicenow_get_incident",
    description="Get details of an existing incident from ServiceNow",
    category="itsm",
    connection_type="servicenow",
    icon="🔍"
)
def get_incident(
    incident_number: str,
    _connection: dict = None
) -> str:
    """
    Get incident details from ServiceNow.
    
    Args:
        incident_number: The incident number (e.g., INC0010001)
        _connection: Injected credentials
    
    Returns:
        Incident details or error message
    """
    if not _connection:
        return "Error: ServiceNow connection not configured."
    
    instance_url = _connection.get("instance_url", "").rstrip("/")
    username = _connection.get("username")
    password = _connection.get("password")
    
    try:
        response = requests.get(
            f"{instance_url}/api/now/table/incident",
            auth=(username, password),
            params={"number": incident_number},
            headers={"Accept": "application/json"},
            timeout=30
        )
        
        if response.ok:
            data = response.json()
            results = data.get("result", [])
            if results:
                inc = results[0]
                return f"""
📋 **Incident: {inc.get('number')}**
- **Short Description:** {inc.get('short_description')}
- **State:** {inc.get('state')}
- **Priority:** {inc.get('priority')}
- **Urgency:** {inc.get('urgency')}
- **Impact:** {inc.get('impact')}
- **Assigned To:** {inc.get('assigned_to', 'Unassigned')}
- **Created:** {inc.get('sys_created_on')}
"""
            else:
                return f"No incident found with number {incident_number}"
        else:
            return f"Error: {response.status_code}"
            
    except requests.exceptions.RequestException as e:
        return f"Connection error: {str(e)}"


@tool(
    name="servicenow_update_incident",
    description="Update an existing incident in ServiceNow",
    category="itsm",
    connection_type="servicenow",
    icon="✏️"
)
def update_incident(
    incident_number: str,
    work_notes: str = "",
    state: str = "",
    assigned_to: str = "",
    _connection: dict = None
) -> str:
    """
    Update an incident in ServiceNow.
    
    Args:
        incident_number: The incident number to update
        work_notes: Work notes to add
        state: New state (1=New, 2=In Progress, 3=On Hold, 6=Resolved, 7=Closed)
        assigned_to: User to assign to
        _connection: Injected credentials
    
    Returns:
        Success or error message
    """
    if not _connection:
        return "Error: ServiceNow connection not configured."
    
    instance_url = _connection.get("instance_url", "").rstrip("/")
    username = _connection.get("username")
    password = _connection.get("password")
    
    # First, get the sys_id of the incident
    try:
        get_response = requests.get(
            f"{instance_url}/api/now/table/incident",
            auth=(username, password),
            params={"number": incident_number, "sysparm_fields": "sys_id"},
            headers={"Accept": "application/json"},
            timeout=30
        )
        
        if not get_response.ok or not get_response.json().get("result"):
            return f"Incident {incident_number} not found."
        
        sys_id = get_response.json()["result"][0]["sys_id"]
        
        # Now update
        payload = {}
        if work_notes:
            payload["work_notes"] = work_notes
        if state:
            payload["state"] = state
        if assigned_to:
            payload["assigned_to"] = assigned_to
        
        if not payload:
            return "No updates specified."
        
        update_response = requests.patch(
            f"{instance_url}/api/now/table/incident/{sys_id}",
            auth=(username, password),
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=30
        )
        
        if update_response.ok:
            return f"✅ Incident {incident_number} updated successfully."
        else:
            return f"Error updating: {update_response.status_code}"
            
    except requests.exceptions.RequestException as e:
        return f"Connection error: {str(e)}"


@tool(
    name="servicenow_list_incidents",
    description="List recent incidents from ServiceNow",
    category="itsm",
    connection_type="servicenow",
    icon="📋"
)
def list_incidents(
    limit: int = 10,
    state: str = "",
    assigned_to_me: bool = False,
    _connection: dict = None
) -> str:
    """
    List incidents from ServiceNow.
    
    Args:
        limit: Maximum number of incidents to return (default 10)
        state: Filter by state (optional)
        assigned_to_me: Only show incidents assigned to the connected user
        _connection: Injected credentials
    
    Returns:
        List of incidents or error message
    """
    if not _connection:
        return "Error: ServiceNow connection not configured."
    
    instance_url = _connection.get("instance_url", "").rstrip("/")
    username = _connection.get("username")
    password = _connection.get("password")
    
    params = {
        "sysparm_limit": limit,
        "sysparm_fields": "number,short_description,state,priority,sys_created_on",
        "sysparm_order_by": "sys_created_on",
        "sysparm_order_direction": "desc"
    }
    
    if state:
        params["state"] = state
    
    try:
        response = requests.get(
            f"{instance_url}/api/now/table/incident",
            auth=(username, password),
            params=params,
            headers={"Accept": "application/json"},
            timeout=30
        )
        
        if response.ok:
            results = response.json().get("result", [])
            if not results:
                return "No incidents found."
            
            output = f"📋 **Recent Incidents ({len(results)}):**\n\n"
            for inc in results:
                output += f"- **{inc.get('number')}**: {inc.get('short_description')[:50]}...\n"
            
            return output
        else:
            return f"Error: {response.status_code}"
            
    except requests.exceptions.RequestException as e:
        return f"Connection error: {str(e)}"
