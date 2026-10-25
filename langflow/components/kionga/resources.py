"""Kionga resource nodes for the Langflow visual canvas.

The adjacent loopback helper supplies a revocable, project-scoped identity.
Neither a Kionga API token nor a model/provider secret enters a flow definition.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from lfx.custom import Component
from lfx.io import BoolInput, DropdownInput, MessageTextInput, Output, StrInput
from lfx.schema import Data
from lfx.schema.message import Message

BASE = "http://127.0.0.1:8890/api/v1"


def request(path: str, payload: object = None) -> object:
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("Invalid Kionga API path")
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="GET" if data is None else "POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise ValueError(f"Kionga rejected this resource request ({error.code})") from error
    except (OSError, ValueError) as error:
        raise ValueError("Kionga resource service is unavailable") from error


class KiongaModels(Component):
    display_name = "Kionga Models"
    description = "List models visible to this workspace's project. Use a model ID with Kionga Model Inference."
    name = "KiongaModels"
    icon = "Database"
    inputs = []
    outputs = [Output(name="models", display_name="Models", method="list_models")]

    def list_models(self) -> Data:
        items = request("/models").get("items", [])
        return Data(data={"models": [
            {key: item.get(key) for key in ("id", "name", "version", "status", "endpoint_url")}
            for item in items
        ]})


class KiongaModelInference(Component):
    display_name = "Kionga Model Inference"
    description = "Invoke an authorized, deployed Kionga model without exposing endpoint credentials."
    name = "KiongaModelInference"
    icon = "Bot"
    inputs = [
        BoolInput(name="refresh_models", display_name="Refresh Kionga models", value=False, real_time_refresh=True),
        DropdownInput(name="model_id", display_name="Deployed model ID", options=[], required=True, combobox=True),
        MessageTextInput(name="input_text", display_name="Input", required=True),
    ]
    outputs = [Output(name="prediction", display_name="Prediction", method="predict")]

    def update_build_config(self, build_config, field_value, field_name=None):
        if field_name == "refresh_models":
            try:
                models = request("/models").get("items", [])
                build_config["model_id"]["options"] = [
                    item["id"] for item in models if item.get("endpoint_url")
                ]
            except ValueError:
                build_config["model_id"]["options"] = []
        return build_config

    def predict(self) -> Message:
        model_id = urllib.parse.quote(self.model_id, safe="")
        result = request(f"/models/{model_id}/predict", {"inputs": [self.input_text]})
        return Message(text=json.dumps(result, ensure_ascii=False))


class KiongaFunctions(Component):
    display_name = "Kionga Function"
    description = "Invoke an authorized Kionga function as an agent tool."
    name = "KiongaFunction"
    icon = "Wrench"
    inputs = [
        StrInput(name="function_name", display_name="Function name", required=True),
        MessageTextInput(name="input_text", display_name="Input", tool_mode=True),
    ]
    outputs = [Output(name="result", display_name="Result", method="invoke")]

    def invoke(self) -> Message:
        name = urllib.parse.quote(self.function_name, safe="")
        result = request(f"/functions/{name}/invoke", {"input": self.input_text})
        return Message(text=json.dumps(result, ensure_ascii=False))


class KiongaStorage(Component):
    display_name = "Kionga Storage"
    description = "List project-authorized object storage buckets."
    name = "KiongaStorage"
    icon = "Database"
    inputs = []
    outputs = [Output(name="buckets", display_name="Buckets", method="list_buckets")]

    def list_buckets(self) -> Data:
        return Data(data={"buckets": request("/storage/buckets")})


class KiongaTools(Component):
    display_name = "Kionga Tools"
    description = "Discover registered tool schemas. Invoke an executable function with Kionga Function."
    name = "KiongaTools"
    icon = "Wrench"
    inputs = []
    outputs = [Output(name="tools", display_name="Tools", method="list_tools")]

    def list_tools(self) -> Data:
        items = request("/tools").get("items", [])
        return Data(data={"tools": [
            {key: item.get(key) for key in ("name", "version", "description", "input_schema", "status")}
            for item in items
        ]})
