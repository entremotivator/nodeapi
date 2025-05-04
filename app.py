import streamlit as st
import requests
import json

st.set_page_config(page_title="n8n Node Manager", layout="wide")

# --- Sidebar for API credentials ---
st.sidebar.header("n8n API Settings")
n8n_api_url = st.sidebar.text_input("n8n API Base URL", value="http://localhost:5678/rest")
api_token = st.sidebar.text_input("API Token", type="password")
workflow_id = st.sidebar.text_input("Workflow ID")

def get_headers():
    return {"Authorization": f"Bearer {api_token}"}

def get_workflow():
    url = f"{n8n_api_url}/workflows/{workflow_id}"
    resp = requests.get(url, headers=get_headers())
    resp.raise_for_status()
    return resp.json()

def update_workflow(workflow_data):
    url = f"{n8n_api_url}/workflows/{workflow_id}"
    resp = requests.put(url, json=workflow_data, headers=get_headers())
    resp.raise_for_status()
    return resp.json()

st.title("n8n Workflow Node Editor")

if not (n8n_api_url and api_token and workflow_id):
    st.info("Please enter your n8n API credentials and workflow ID in the sidebar.")
    st.stop()

try:
    workflow = get_workflow()
    nodes = workflow['nodes']
except Exception as e:
    st.error(f"Error fetching workflow: {e}")
    st.stop()

# --- Display all nodes ---
st.subheader("All Nodes in Workflow")
for i, node in enumerate(nodes):
    with st.expander(f"{i+1}. {node['name']} ({node['type']})"):
        st.write(f"ID: {node['id']}")
        st.write("Parameters:")
        st.json(node['parameters'])
        if 'credentials' in node:
            st.write("Credentials:")
            st.json(node['credentials'])

# --- Node selection for editing ---
st.divider()
st.subheader("Edit a Node")
node_names = [f"{i+1}. {node['name']} ({node['type']})" for i, node in enumerate(nodes)]
selected_idx = st.selectbox("Select node to edit:", range(len(nodes)), format_func=lambda i: node_names[i])
selected_node = nodes[selected_idx]

with st.form("edit_node_form"):
    new_name = st.text_input("Node Name", value=selected_node["name"])
    new_type = st.text_input("Node Type", value=selected_node["type"])
    # Parameters editing as JSON
    new_parameters = st.text_area(
        "Parameters (JSON)", 
        value=json.dumps(selected_node["parameters"], indent=2),
        height=200
    )
    submitted = st.form_submit_button("Save Changes")

    if submitted:
        try:
            # Validate JSON
            new_params_obj = json.loads(new_parameters)
            # Update node
            selected_node["name"] = new_name
            selected_node["type"] = new_type
            selected_node["parameters"] = new_params_obj
            workflow["nodes"][selected_idx] = selected_node
            update_workflow(workflow)
            st.success("Node updated successfully! Refresh to see changes.")
        except Exception as e:
            st.error(f"Error updating node: {e}")
