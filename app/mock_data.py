import networkx as nx
from app.dataset_pipeline import get_dataset_graph, reset_dataset_pipeline


def generate_synthetic_upi_graph() -> nx.DiGraph:
    """Returns the NetworkX DiGraph constructed from the Prototype 2 transaction datasheet."""
    return get_dataset_graph()


def get_graph() -> nx.DiGraph:
    """Returns the singleton graph from the transaction dataset pipeline."""
    return get_dataset_graph()


def reset_graph() -> nx.DiGraph:
    """Reloads the dataset CSV and resets the graph pipeline."""
    return reset_dataset_pipeline()
