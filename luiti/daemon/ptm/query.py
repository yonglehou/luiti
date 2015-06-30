# -*-coding:utf-8-*-

__all__ = ["Query"]

from etl_utils import cached_property

from ..graph import Graph
from ..template import Template


# TODO more modular
class QueryBuilder(object):
    """
    Construct a query builder.

    All propertyies are generated lazily by using `cached_property`, as in a DAG.
    """

    def __init__(self, ptm, raw_params):
        assert isinstance(raw_params, dict), raw_params

        self.raw_params = raw_params
        self.ptm = ptm

    @cached_property
    def query_params(self):
        return self.ptm.generate_query_params()

    @cached_property
    def selected_query(self):
        return self.ptm.generate_selected_query(self.default_query,
                                                self.raw_params,
                                                self.selected_packages)

    @cached_property
    def default_query(self):
        return self.ptm.generate_default_query(self.query_params)

    @cached_property
    def default_packages(self):
        return self.ptm.current_luiti_visualiser_env["package_config"]["defaults"]

    @cached_property
    def selected_packages(self):
        return self.raw_params.get("luiti_package", self.default_packages)

    @cached_property
    def selected_task_cls_names(self):
        result = set(self.raw_params.get("task_cls", []))

        # modify other cached_property
        self.selected_query["task_cls"] = list(result)

        return result

    @cached_property
    def total_task_instances(self):
        return self.ptm.generate_total_task_instances(self.default_query,
                                                      self.selected_query,
                                                      self.ptm.task_class_names)

    @cached_property
    def selected_task_instances(self):
        # TODO filter nodes
        result = filter(lambda ti: ti.package_name in self.selected_packages,
                        self.total_task_instances)
        result = sorted(list(set(result)))

        # To avoid only self is in the graph.
        # If select task class, then to find linked task instances.
        if self.selected_task_cls_names:
            pure_selected_task_instances = [ti for ti in result if ti.task_clsname in self.selected_task_cls_names]
            pure_linked = set([])
            for ti in pure_selected_task_instances:
                for t2 in self.graph_infos_python["requires"]["total"][ti]:
                    pure_linked.add(t2)
                for t2 in self.graph_infos_python["upons"]["total"][ti]:
                    pure_linked.add(t2)
            # filter that tasks are linked, in current task_classes.
            result = [ti for ti in result if ti in pure_linked]
            result.extend(pure_selected_task_instances)
            result = list(set(result))
        return result

    @cached_property
    def graph_infos_data(self):
        return Graph.analysis_dependencies_between_nodes(self.total_task_instances,
                                                         self.selected_packages)

    @cached_property
    def graph_infos_python(self):
        return self.graph_infos_data["python"]

    @cached_property
    def nodes(self):
        return [Template.a_node(ti) for ti in self.selected_task_instances]

    @cached_property
    def nodeid_to_node_dict(self):
        return {node["id"]: node for node in self.nodes}

    @cached_property
    def edges(self):
        return Template.edges_from_nodes(self.selected_task_instances)

    @cached_property
    def nodes_groups(self):
        return Graph.split_edges_into_groups(self.edges,
                                             self.nodes,
                                             self.selected_task_instances)

    @cached_property
    def nodes_groups_in_view(self):
        return [sorted(list(nodes_set)) for nodes_set in self.nodes_groups]

    @cached_property
    def task_instance_repr_to_info(self):
        return self.ptm.generate_task_instance_repr_to_info(self.selected_task_instances)

    @cached_property
    def result(self):
        return {
            "query_params": self.query_params,

            "title": "A DAG timely visualiser.",
            "selected_query": self.selected_query,
            "default_query": self.default_query,
            "luiti_visualiser_env": self.ptm.current_luiti_visualiser_env,

            "task_class_names": self.ptm.task_class_names,
            "task_package_names": self.ptm.task_package_names,
            "task_clsname_to_package_name": self.ptm.task_clsname_to_package_name,
            "package_to_task_clsnames": self.ptm.package_to_task_clsnames,

            "nodes": self.nodes,
            "edges": self.edges,
            "nodes_groups": self.nodes_groups_in_view,
            "nodeid_to_node_dict": self.nodeid_to_node_dict,

            "graph_infos": self.graph_infos_data["json"],
            "task_instance_repr_to_info": self.task_instance_repr_to_info,

            "errors": {
                "load_tasks": self.ptm.load_all_tasks_result["failure"],
            }
        }


class Query(object):
    """
    Use params to query some data from luiti.
    """

    def get_env(self, raw_params=dict()):
        """
        Generate all data needed.
        """
        # total_task_instances = self.generate_total_task_instances(default_query, selected_query, selected_task_cls_names)
        ptm = self

        qb = QueryBuilder(ptm, raw_params)
        return qb.result