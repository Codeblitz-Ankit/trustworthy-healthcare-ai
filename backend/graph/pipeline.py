"""LangGraph pipeline definition for the healthcare verification state machine."""

from langgraph.graph import END, StateGraph

try:
    from .nodes import (
        aggregator_node,
        consistency_node,
        grounding_node,
        hard_safety_node,
        input_safety_node,
        irrelevant_change_node,
        proposer_node,
    )
    from .state import HealthcareState
except (ImportError, ValueError):
    from backend.graph.nodes import (
        aggregator_node,
        consistency_node,
        grounding_node,
        hard_safety_node,
        input_safety_node,
        irrelevant_change_node,
        proposer_node,
    )
    from backend.graph.state import HealthcareState

# Define the StateGraph builder using HealthcareState
builder = StateGraph(HealthcareState)

# Add pipeline nodes
builder.add_node("input_safety", input_safety_node)
builder.add_node("proposer", proposer_node)
builder.add_node("hard_safety", hard_safety_node)
builder.add_node("grounding", grounding_node)
builder.add_node("consistency", consistency_node)
builder.add_node("irrelevant_change", irrelevant_change_node)
builder.add_node("aggregator", aggregator_node)

# Set the workflow entry point
builder.set_entry_point("input_safety")

# Define execution edges:
# input_safety -> proposer -> hard_safety -> grounding -> consistency -> irrelevant_change -> aggregator -> END
builder.add_edge("input_safety", "proposer")
builder.add_edge("proposer", "hard_safety")
builder.add_edge("hard_safety", "grounding")
builder.add_edge("grounding", "consistency")
builder.add_edge("consistency", "irrelevant_change")
builder.add_edge("irrelevant_change", "aggregator")
builder.add_edge("aggregator", END)

# Compile into an executable LangGraph pipeline
healthcare_pipeline = builder.compile()

__all__ = ["builder", "healthcare_pipeline"]
