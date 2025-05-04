import streamlit as st
import requests
import json
import logging

# --- Demo n8n API setup ---
N8N_HOST = "agentonline-u29564.vm.elestio.app"
N8N_PORT = ""  # No port for cloud-hosted n8n
N8N_BASE_PATH = "api/v1"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NDI5NWRjYS01YTIxLTQzZDMtYTA1OS1jOTA5YTQ5ZjlkYTEiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzM2NTQ4NDY0fQ.E0kssDoB4sVrqTuJLBO1Avl2Wxi8cYOzmzABbc-0DbM"

API_URLS = {
    "workflows": f"{N8N_BASE_PATH}/workflows",
    "executions": f"{N8N_BASE_PATH}/executions",
    "credentials": f"{N8N_BASE_PATH}/credentials",
    "tags": f"{N8N_BASE_PATH}/tags",
    "users": f"{N8N_BASE_PATH}/users",
    "variables": f"{N8N_BASE_PATH}/variables"
}

def make_api_request(method, endpoint, headers=None, data=None, params=None):
    url = f"https://{N8N_HOST}/{endpoint}"  # Use https for cloud
    headers = headers or {"accept": "application/json", "X-N8N-API-KEY": API_KEY}
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError("Invalid HTTP method")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"API error: {e}")
        st.error(f"API error: {e}")
        return None

def fetch_workflows(cursor=None, limit=10, search_query=None):
    params = {"active": "true", "limit": limit}
    if cursor:
        params["cursor"] = cursor
    if search_query:
        params["search"] = search_query
    return make_api_request("GET", API_URLS["workflows"], params=params)

def fetch_workflow_by_id(workflow_id):
    return make_api_request("GET", f"{API_URLS['workflows']}/{workflow_id}")

def toggle_workflow_status(workflow_id, status):
    data = {"active": status}
    return make_api_request("PATCH", f"{API_URLS['workflows']}/{workflow_id}", data=data)

def create_workflow(name, active):
    data = {"name": name, "active": active}
    return make_api_request("POST", API_URLS["workflows"], data=data)

def delete_workflow(workflow_id):
    return make_api_request("DELETE", f"{API_URLS['workflows']}/{workflow_id}")

def fetch_executions(workflow_id=None, limit=10):
    params = {"limit": limit}
    if workflow_id:
        params["workflowId"] = workflow_id
    return make_api_request("GET", API_URLS["executions"], params=params)

# --- Streamlit UI ---
st.set_page_config(page_title="n8n Workflow Manager", layout="wide")
st.title("n8n Workflow Manager Demo")

# --- Workflow Search and List ---
st.sidebar.header("Workflow Controls")
search_query = st.sidebar.text_input("Search workflows")
limit = st.sidebar.slider("Workflows per page", 1, 50, 10)
workflows_data = fetch_workflows(limit=limit, search_query=search_query)

if workflows_data and "data" in workflows_data:
    workflows = workflows_data["data"]
    workflow_names = [f"{wf['name']} (ID: {wf['id']})" for wf in workflows]
    workflow_ids = [wf['id'] for wf in workflows]
    selected_idx = st.sidebar.selectbox("Select Workflow", range(len(workflows)), format_func=lambda i: workflow_names[i])
    selected_workflow_id = workflow_ids[selected_idx]
else:
    st.warning("No workflows found or API error.")
    st.stop()

# --- Workflow Actions ---
st.sidebar.markdown("### Actions")
if st.sidebar.button("Create New Workflow"):
    new_name = st.text_input("New Workflow Name", value="My Workflow")
    if st.button("Confirm Create"):
        create_workflow(new_name, active=False)
        st.experimental_rerun()
if st.sidebar.button("Delete Selected Workflow"):
    if st.sidebar.confirm("Are you sure you want to delete this workflow?"):
        delete_workflow(selected_workflow_id)
        st.experimental_rerun()

# --- Workflow Details ---
workflow = fetch_workflow_by_id(selected_workflow_id)
if not workflow:
    st.error("Failed to load workflow details.")
    st.stop()

st.header(f"Workflow: {workflow['name']} (ID: {workflow['id']})")
st.write(f"Active: {workflow['active']}")
if st.button("Toggle Active"):
    toggle_workflow_status(workflow['id'], not workflow['active'])
    st.experimental_rerun()

# --- Nodes List and Editing ---
st.subheader("Nodes in Workflow")
nodes = workflow.get("nodes", [])
for i, node in enumerate(nodes):
    with st.expander(f"{i+1}. {node['name']} ({node['type']})"):
        st.write(f"ID: {node['id']}")
        st.write("Parameters:")
        st.json(node['parameters'])
        if 'credentials' in node:
            st.write("Credentials:")
            st.json(node['credentials'])

# --- Node Editing ---
st.subheader("Edit a Node")
if nodes:
    node_names = [f"{i+1}. {node['name']} ({node['type']})" for i, node in enumerate(nodes)]
    edit_idx = st.selectbox("Select node to edit:", range(len(nodes)), format_func=lambda i: node_names[i])
    edit_node = nodes[edit_idx]
    with st.form("edit_node_form"):
        new_name = st.text_input("Node Name", value=edit_node["name"])
        new_type = st.text_input("Node Type", value=edit_node["type"])
        new_parameters = st.text_area("Parameters (JSON)", value=json.dumps(edit_node["parameters"], indent=2), height=200)
        submitted = st.form_submit_button("Save Node Changes")
        if submitted:
            try:
                edit_node["name"] = new_name
                edit_node["type"] = new_type
                edit_node["parameters"] = json.loads(new_parameters)
                workflow["nodes"][edit_idx] = edit_node
                make_api_request("PATCH", f"{API_URLS['workflows']}/{workflow['id']}", data=workflow)
                st.success("Node updated! Reloading...")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Error updating node: {e}")

# --- Show Executions ---
st.subheader("Recent Executions")
executions = fetch_executions(workflow_id=workflow['id'], limit=5)
if executions and "data" in executions:
    for exe in executions["data"]:
        st.write(f"Execution ID: {exe['id']}, Status: {exe['status']}, Started: {exe['startedAt']}")
else:
    st.info("No executions found.")

st.markdown("---")
st.caption("Demo app for n8n API management. Powered by Streamlit.")
