import streamlit as st
import requests
import json
import logging

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="n8n Workflow Manager", layout="wide")
st.title("🛠️ n8n Workflow Manager")

# ------------------ SIDEBAR: API CONNECTION ------------------
st.sidebar.header("🔑 n8n API Connection")

def sidebar_text_input(key, label, default, **kwargs):
    return st.sidebar.text_input(label, value=st.session_state.get(key, default), key=key, **kwargs)

sidebar_text_input("n8n_host", "n8n Host", "agentonline-u29564.vm.elestio.app")
sidebar_text_input("n8n_port", "n8n Port (leave blank for default)", "")
sidebar_text_input("n8n_base_path", "n8n API Base Path", "api/v1")
st.session_state["api_key"] = st.sidebar.text_input("API Key", type="password")

# ------------------ API UTILS ------------------
def get_api_base():
    host = st.session_state["n8n_host"]
    port = f":{st.session_state['n8n_port']}" if st.session_state["n8n_port"] else ""
    protocol = "https" if host.startswith("https") or host.endswith(".app") else "http"
    return f"{protocol}://{host}{port}/{st.session_state['n8n_base_path'].strip('/')}".rstrip("/")

def api_url(endpoint):
    return f"{get_api_base()}/{endpoint.strip('/')}"

def make_api_request(method, endpoint, headers=None, data=None, params=None):
    url = api_url(endpoint)
    headers = headers or {
        "accept": "application/json",
        "X-N8N-API-KEY": st.session_state["api_key"]
    }
    try:
        response = requests.request(method, url, headers=headers, json=data, params=params)
        response.raise_for_status()
        if response.content:
            return response.json()
        return {}
    except requests.RequestException as e:
        logging.error(f"API error: {e}")
        st.error(f"API error: {e}")
        return None

# ------------------ API FUNCTIONS ------------------
def fetch_workflows(limit=50, search_query=None):
    params = {"limit": limit}
    if search_query:
        params["search"] = search_query
    return make_api_request("GET", "workflows", params=params)

def fetch_workflow_by_id(workflow_id):
    return make_api_request("GET", f"workflows/{workflow_id}")

def toggle_workflow_status(workflow_id, status):
    return make_api_request("PATCH", f"workflows/{workflow_id}", data={"active": status})

def create_workflow(name, active):
    return make_api_request("POST", "workflows", data={"name": name, "active": active})

def delete_workflow(workflow_id):
    return make_api_request("DELETE", f"workflows/{workflow_id}")

def fetch_executions(workflow_id=None, limit=5):
    params = {"limit": limit}
    if workflow_id:
        params["workflowId"] = workflow_id
    return make_api_request("GET", "executions", params=params)

# ------------------ SIDEBAR CONTROLS ------------------
st.sidebar.header("📋 Workflow Controls")

with st.sidebar.expander("🔍 Search and Load Workflows"):
    search_query = st.text_input("Search by name")
    limit = st.slider("Max workflows", 1, 100, 25)
    if st.button("🔄 Refresh List"):
        st.session_state["refresh"] = True

# ------------------ FETCH WORKFLOWS ------------------
workflows_data = fetch_workflows(limit=limit, search_query=search_query)
if not workflows_data or "data" not in workflows_data:
    st.error("No workflows found or API error.")
    st.stop()

workflows = workflows_data["data"]
workflow_map = {f"{wf['name']} (Active: {'✅' if wf['active'] else '❌'})": wf['id'] for wf in workflows}

selected_name = st.selectbox("📄 Select a Workflow", options=list(workflow_map.keys()))
selected_workflow_id = workflow_map[selected_name]

# ------------------ WORKFLOW ACTIONS ------------------
st.sidebar.markdown("### ➕ Create Workflow")
with st.sidebar.form("create_workflow_form"):
    new_name = st.text_input("New Workflow Name")
    new_active = st.checkbox("Active", value=True)
    create_submitted = st.form_submit_button("Create")
    if create_submitted and new_name:
        result = create_workflow(new_name, active=new_active)
        if result:
            st.sidebar.success(f"Workflow '{new_name}' created.")
            st.rerun()
        else:
            st.sidebar.error("Failed to create workflow.")

st.sidebar.markdown("### ❌ Delete Workflow")
with st.sidebar.form("delete_workflow_form"):
    confirm_delete = st.checkbox("Confirm delete")
    delete_submitted = st.form_submit_button("Delete Selected")
    if delete_submitted and confirm_delete:
        result = delete_workflow(selected_workflow_id)
        if result is not None:
            st.sidebar.success("Workflow deleted.")
            st.rerun()
        else:
            st.sidebar.error("Failed to delete workflow.")

# ------------------ WORKFLOW DETAILS ------------------
workflow = fetch_workflow_by_id(selected_workflow_id)
if not workflow:
    st.error("Failed to load workflow details.")
    st.stop()

st.header(f"🧾 Workflow: {workflow['name']} (ID: {workflow['id']})")
st.write(f"**Status:** {'✅ Active' if workflow['active'] else '❌ Inactive'}")

# Toggle status
with st.form("toggle_active_form"):
    toggle_label = "Deactivate" if workflow['active'] else "Activate"
    toggle_submitted = st.form_submit_button(toggle_label)
    if toggle_submitted:
        result = toggle_workflow_status(workflow['id'], not workflow['active'])
        if result:
            st.success(f"Workflow {'activated' if not workflow['active'] else 'deactivated'}.")
            st.rerun()
        else:
            st.error("Failed to toggle workflow status.")

# ------------------ NODE VIEW AND EDIT ------------------
st.subheader("🔗 Workflow Nodes")
nodes = workflow.get("nodes", [])
if nodes:
    for i, node in enumerate(nodes):
        with st.expander(f"{i+1}. {node['name']} ({node['type']})"):
            st.write(f"**ID:** {node['id']}")
            st.json(node["parameters"])
            if "credentials" in node:
                st.write("**Credentials:**")
                st.json(node["credentials"])

    st.subheader("✏️ Edit a Node")
    node_names = [f"{i+1}. {node['name']} ({node['type']})" for i, node in enumerate(nodes)]
    edit_node_idx = st.selectbox("Select node to edit:", range(len(nodes)), format_func=lambda i: node_names[i])
    edit_node = nodes[edit_node_idx]

    with st.form("edit_node_form"):
        new_name = st.text_input("Node Name", value=edit_node["name"])
        new_type = st.text_input("Node Type", value=edit_node["type"])
        new_parameters = st.text_area("Parameters (JSON)", value=json.dumps(edit_node["parameters"], indent=2), height=200)
        node_submitted = st.form_submit_button("Save Node Changes")
        if node_submitted:
            try:
                edit_node["name"] = new_name
                edit_node["type"] = new_type
                edit_node["parameters"] = json.loads(new_parameters)
                workflow["nodes"][edit_node_idx] = edit_node
                result = make_api_request("PATCH", f"workflows/{workflow['id']}", data=workflow)
                if result:
                    st.success("Node updated successfully.")
                else:
                    st.error("Failed to update node.")
            except Exception as e:
                st.error(f"Error parsing parameters: {e}")
else:
    st.warning("No nodes found in this workflow.")

# ------------------ EXECUTIONS ------------------
st.subheader("🕒 Recent Executions")
executions = fetch_executions(workflow_id=workflow['id'], limit=5)
if executions and "data" in executions:
    for exe in executions["data"]:
        with st.expander(f"Execution ID: {exe['id']}"):
            st.write(f"**Status:** {exe['status']}")
            st.write(f"**Started At:** {exe['startedAt']}")
            st.write(f"**Mode:** {exe.get('mode', 'N/A')}")
            st.write(f"**Finished:** {exe.get('finished', 'N/A')}")
            if 'error' in exe:
                st.error(f"Error: {exe['error'].get('message', 'No message')}")
else:
    st.info("No executions found.")
