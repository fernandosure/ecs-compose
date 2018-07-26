#!/usr/bin/python
from ecs_compose import VERSION
from utils import merger, get_ecs_service_diff
from ecs import EcsClient, EcsTaskDefinition
from stack_definition import StackDefinition
from deploy import deploy_new_ecs_service, destroy_ecs_service
import yaml
import click


@click.group()
@click.version_option(version=VERSION, prog_name="ecs-compose")
def cli():
    pass


@cli.group()
def cluster():
    pass


@cli.group()
def service():
    pass


@cluster.command()
@click.argument("cluster")
@click.option("-f", "--stackfile", required=True, type=click.File("rb"), multiple=True, default="stackfile.yml", help="the name of the stackfile")
@click.option("--redeploy", is_flag=True, default=False, help="If you want to force a new deploy using its current settings")
def deploy(cluster, stackfile, redeploy):
    client = EcsClient()
    ecs_cluster = client.get_single_cluster(cluster)

    if ecs_cluster is None:
        click.secho("cluster does not exists")
        return

    json_stack = {}
    for sf in stackfile:
        json_stack = merger.merge(json_stack, yaml.load(sf.read()))
    stack_definition = StackDefinition(json_stack)

    click.secho("retrieving current services state...")
    services = ecs_cluster.get_all_services()
    for svc in stack_definition.services:
        service = next((x for x in services if x.name.lower() == svc.name.lower()), None)
        if service:
            old_td = EcsTaskDefinition.from_arn(service.task_definition_arn)
            diff = get_ecs_service_diff(service, old_td, svc)
            if len(diff) > 0 or redeploy:
                if diff.get(u'image', None) or diff.get(u'environment', None):
                    new_td = svc.get_task_definition(cluster)
                    new_td = new_td.register_as_new_task_definition()
                    service.task_definition_arn = new_td.arn
                    click.secho("deploying taskDefinition version:{} of {}".format(new_td.revision, service.name))

                service.desired_count = svc.desired_count
                service.update_service()
            else:
                click.secho("skipping deployment for {} there are no new changes in the taskDefinition".format(service.name))
        else:
            deploy_new_ecs_service(cluster, stack_definition, svc)


@cluster.command()
@click.argument("cluster")
@click.confirmation_option(help='Are you sure you want to do this?')
def destroy(cluster):
    client = EcsClient()
    ecs_cluster = client.get_single_cluster(cluster)

    if ecs_cluster is None:
        click.secho("cluster does not exists")
        return

    click.secho("retrieving current services state...")
    services = ecs_cluster.get_all_services()
    for service in services:
        destroy_ecs_service(cluster, service.arn)


@cluster.command()
@click.argument("cluster")
def describe(cluster):
    client = EcsClient()
    ecs_cluster = client.get_single_cluster(cluster)

    if ecs_cluster is None:
        click.secho("cluster does not exists")
        return

    click.secho("retrieving current services state...")
    services = ecs_cluster.get_all_services()
    result = {"services": []}
    for service in services:

        td = EcsTaskDefinition.from_arn(service.task_definition_arn)

        svc = {
            service.name: {
                "image": td.containers[0].image}
        }
        if service.running_count != 1:
            svc[service.name]['desired_count'] = service.running_count

        result["services"].append(svc)
    print yaml.safe_dump(result, encoding="utf-8", default_flow_style=False)


@service.command()
@click.argument("cluster")
@click.option("-s", "--service", required=True, help="the name of the service to destroy")
@click.confirmation_option(help='Are you sure you want to do this?')
def destroy(cluster, service):
    client = EcsClient()
    ecs_cluster = client.get_single_cluster(cluster)

    if ecs_cluster is None:
        click.secho("cluster does not exists")
        return

    ecs_service = ecs_cluster.get_single_service(service)
    if ecs_service is None:
        click.secho("Service does not exists")

    destroy_ecs_service(cluster, ecs_service.arn)


if __name__ == "__main__":
    cli()

