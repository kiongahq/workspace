ARG LANGFLOW_IMAGE=docker.io/langflowai/langflow:1.13.0
FROM ${LANGFLOW_IMAGE}
COPY --chown=1000:1000 langflow/components /app/kionga-components
ENV LANGFLOW_COMPONENTS_PATH=/app/kionga-components
ENV LANGFLOW_AGENTIC_EXPERIENCE=false
