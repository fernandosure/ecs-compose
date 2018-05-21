#!/usr/bin/python
from ecs import launch_or_update_stack, destroy_ecs_cluster, destroy_ecs_service, restart_cluster, describe_ecs_cluster
from stack_definition import StackDefinition
from utils import merger

import yaml
import argparse


def main():
    # create the top-level parser

    parser = argparse.ArgumentParser(description='ECS Compose CLI')
    subparsers = parser.add_subparsers(title="ECS Compose CLI Commands", dest="cmd")

    # create the parser for the "cluster" command
    cluster_parser = subparsers.add_parser('cluster', help="cluster related operations")
    cluster_subparsers = cluster_parser.add_subparsers(title="ECS cluster commands", dest="subcmd")

    deploy_cluster_parser = cluster_subparsers.add_parser('deploy', help='Deploys the services defined in the stackfile')
    deploy_cluster_parser.add_argument('--name', '-n', required=True, help='name of the cluster', dest="cluster_name")
    deploy_cluster_parser.add_argument('--file', '-f', required=True, nargs='+', type=argparse.FileType('r'),
                                       help='the name of the stackfile')
    deploy_cluster_parser.set_defaults(func=launch_or_update_stack)

    deploy_cluster_parser = cluster_subparsers.add_parser('destroy', help='Destroys the cluster with its services and stack definitions')
    deploy_cluster_parser.add_argument('--name', '-n', required=True, help='name of the cluster', dest="cluster_name")
    deploy_cluster_parser.set_defaults(func=destroy_ecs_cluster)

    restart_cluster_parser = cluster_subparsers.add_parser('restart', help='Restart the cluster with its services and tasks')
    restart_cluster_parser.add_argument('--name', '-n', required=True, help='name of the cluster', dest="cluster_name")
    restart_cluster_parser.set_defaults(func=restart_cluster)

    describe_cluster_parser = cluster_subparsers.add_parser('describe', help='Describe cluster as yml definition')
    describe_cluster_parser.add_argument('--name', '-n', required=True, help='name of the cluster', dest='cluster_name')
    describe_cluster_parser.set_defaults(func=describe_ecs_cluster)

    # create the parser for the "service" command
    service_parser = subparsers.add_parser('service', help="service related operations")
    service_subparsers = service_parser.add_subparsers(title="ECS tool service commands", dest="subcmd")

    destroy_service_parser = service_subparsers.add_parser('destroy', help='Destroys the service with its load balancers and stack definitions')
    destroy_service_parser.add_argument('--name', '-n', required=True, help='name of the cluster', dest="cluster_name")
    destroy_service_parser.add_argument('--service', '-s', required=True, help='name of the service', dest="service_name")
    destroy_service_parser.set_defaults(func=destroy_ecs_service)

    args = parser.parse_args()
    if args.cmd == "cluster":
        if args.subcmd == "deploy":
            json_stack = {}
            for yml_file in args.file:
                json_stack = merger.merge(json_stack, yaml.load(yml_file.read()))
            stack = StackDefinition(json_stack)
            args.func(args.cluster_name, stack)
        elif args.subcmd == "destroy" or args.subcmd == "restart":
            args.func(args.cluster_name)

        elif args.subcmd == "describe":
            result = args.func(args.cluster_name)
            print yaml.safe_dump(result, encoding='utf-8', default_flow_style=False)

    if args.cmd == "service":
        if args.subcmd == "destroy":
            args.func(args.cluster_name, args.service_name)


if __name__ == "__main__":
    main()
