import boto3
import json

# Let's use Amazon ECS
ecs = boto3.client('ecs')
ec2 = boto3.client('ec2')
elbv2 = boto3.client('elbv2')
route53 = boto3.client('route53')
autoscaling = boto3.client('autoscaling')


def create_ecs_cluster(stack_name, stack):
    response = ecs.create_cluster(clusterName=stack_name)
    #
    # response = autoscaling.create_launch_configuration(
    #     LaunchConfigurationName="{}-launch-configuration".format(stack_name),
    #     ImageId="ami-275ffe31",
    #     KeyName="osigu-ecs-keypair",
    #     SecurityGroups=stack.vpc.security_groups.private,
    #     UserData=open("userdata.cfg").read().replace("{cluster}", stack_name),
    #     InstanceType="r4.large",
    #     IamInstanceProfile="ecs-instance-profile"
    # )
    #
    # response = autoscaling.create_auto_scaling_group(
    #     AutoScalingGroupName="{}-autoscaling-group".format(stack_name),
    #     LaunchConfigurationName="{}-launch-configuration".format(stack_name),
    #     MaxSize=5,
    #     MinSize=1,
    #     VPCZoneIdentifier=",".join(stack.vpc.subnets.private),
    #     Tags=[
    #         {
    #             'ResourceId': "{}-autoscaling-group".format(stack_name),
    #             'ResourceType': 'auto-scaling-group',
    #             'PropagateAtLaunch': True,
    #             'Key': 'Name',
    #             'Value': stack_name,
    #         }
    #     ]
    # )

    response = autoscaling.create_launch_configuration(
        LaunchConfigurationName="{}-launch-configuration-spot".format(stack_name),
        ImageId="ami-20ff515a",
        KeyName="osigu-ecs-keypair",
        SecurityGroups=stack.vpc.security_groups.private,
        UserData=open("userdata.cfg").read().replace("{cluster}", stack_name),
        InstanceType="r4.large",
        IamInstanceProfile="ecs-instance-profile",
        SpotPrice="0.133"
    )

    response = autoscaling.create_auto_scaling_group(
        AutoScalingGroupName="{}-autoscaling-group-spot".format(stack_name),
        LaunchConfigurationName="{}-launch-configuration-spot".format(stack_name),
        MaxSize=5,
        MinSize=1,
        VPCZoneIdentifier=",".join(stack.vpc.subnets.private),
        Tags=[
            {
                'ResourceId': "{}-autoscaling-group-spot".format(stack_name),
                'ResourceType': 'auto-scaling-group',
                'PropagateAtLaunch': True,
                'Key': 'Name',
                'Value': stack_name,
            }
        ]
    )


def restart_cluster(stack_name):

    list_tasks_response = ecs.list_tasks(cluster=stack_name, desiredStatus='RUNNING')
    tasks = list_tasks_response["taskArns"]

    while list_tasks_response.get("nextToken") is not None:
        list_tasks_response = ecs.list_tasks(nextToken=list_tasks_response["nextToken"])
        tasks.extend(list_tasks_response["taskArns"])

    for task in tasks:
        ecs.stop_task(cluster=stack_name, task=task, reason='Restarted by ECS-Tool')


def launch_or_update_stack(stack_name, stack):

    for service in stack.services:
        family = "%s-%s" % (stack_name, service.name)
        print "registering container: %s" % service.name
        container_definition = {
                  "name": service.name,
                  "image": service.image,
                  "essential": True,
                  "memory":  service.memory,
                  "hostname": service.name,
                  "privileged": service.privileged,
                  "logConfiguration": {
                        "logDriver": "gelf",
                        "options": {
                            "gelf-address": "udp://logstash.osigu.dev:12201",
                            "tag": stack_name
                        }
                    }
                }

        volumes = [
            {
                'name': x["name"],
                'host': {
                    'sourcePath': x["host"]
                }
            } for x in service.volumes
        ]

        container_definition["mountPoints"] = [
            {
                'sourceVolume': x["name"],
                'containerPath': x["container"],
                'readOnly': False
            } for x in service.volumes
        ]

        # ENVIRONMENTS
        environments = service.environment
        environments.extend([g for g in stack.defaults.environment if len([v for v in service.environment if v["name"] == g["name"]]) == 0])
        container_definition["environment"] = environments

        # PORTS
        container_definition["portMappings"] = service.ports

        # Create a task definition
        register_task_definition_response = ecs.register_task_definition(family=family, networkMode="host", containerDefinitions=[container_definition], volumes=volumes)
        print("task_definition: %s response: %s" % (service.name, register_task_definition_response.get("ResponseMetadata",{}).get("HTTPStatusCode")))

        if service.type == "service":
            # Search for an already created service
            describe_services_response = ecs.describe_services(cluster=stack_name, services=[service.name])

            load_balancers = []
            if len(service.elb) > 0:

                for elb in service.elb:

                    elb_name = "{}{}-lb".format(family, "-{}".format(elb.name) if len(elb.name) > 0 else "")

                    try:
                        describe_load_balancers_response = elbv2.describe_load_balancers(Names=[elb_name])
                    except:
                        describe_load_balancers_response = {"LoadBalancers":[]}

                    # if not exists a load balancer for the service
                    if len(describe_load_balancers_response["LoadBalancers"]) == 0:

                        print "creating loadbalancer: %s" % elb_name
                        create_load_balancer_response = elbv2.create_load_balancer(
                            Name=elb_name,
                            Subnets=stack.vpc.subnets.private if elb.type == "private" else stack.vpc.subnets.public,
                            SecurityGroups=stack.vpc.security_groups.private if elb.type == "private" else stack.vpc.security_groups.public,
                            Scheme="internal" if elb.type == "private" else "internet-facing",
                            Tags=[
                                {
                                    "Key": "ecs_cluster",
                                    "Value": stack_name
                                }
                            ],
                            IpAddressType="ipv4"
                        )
                        load_balancer_arn = create_load_balancer_response["LoadBalancers"][0]["LoadBalancerArn"]
                        r53_hosted_zone_id = create_load_balancer_response["LoadBalancers"][0]["CanonicalHostedZoneId"]
                        load_balancer_dns = create_load_balancer_response["LoadBalancers"][0]["DNSName"]

                        print "load balancer created successfully arn:%s hosted-zone-id:%s dns:%s" % (load_balancer_arn, r53_hosted_zone_id, load_balancer_dns)

                        print "creating target group: %s" % elb_name
                        create_target_group_response = elbv2.create_target_group(
                            Name=elb_name,
                            Protocol="HTTP",
                            Port=elb.ports.container,
                            VpcId=stack.vpc.id,
                            HealthCheckProtocol=elb.healthcheck.protocol,
                            HealthCheckPort=str(elb.healthcheck.port if elb.healthcheck.port else elb.ports.container),
                            HealthCheckPath=elb.healthcheck.path,
                            HealthCheckIntervalSeconds=elb.healthcheck.interval_seconds,
                            HealthCheckTimeoutSeconds=elb.healthcheck.timeout_seconds,
                            HealthyThresholdCount=elb.healthcheck.healthy_threshold_count,
                            UnhealthyThresholdCount=elb.healthcheck.unhealthy_threshold_count
                        )
                        target_group_arn = create_target_group_response["TargetGroups"][0]["TargetGroupArn"]

                        # CREATE LISTENER
                        print "creating listener: %s" % elb_name
                        elbv2.create_listener(
                            LoadBalancerArn=load_balancer_arn,
                            Protocol=elb.protocol,
                            Port=elb.ports.public,
                            Certificates=elb.certificates,
                            DefaultActions=[
                                {
                                    'Type': 'forward',
                                    'TargetGroupArn': target_group_arn,
                                }
                            ]
                        )

                        load_balancers = [
                            {
                                'targetGroupArn': target_group_arn,
                                'containerName': service.name,
                                'containerPort': elb.ports.container,
                            }
                        ]

                        # Update Route53 recordset
                        if elb.dns is not None:
                            print "updating route53 recordset"
                            change_resource_record_set_response = route53.change_resource_record_sets(
                                HostedZoneId=elb.dns.hosted_zone_id,
                                ChangeBatch={
                                    'Changes': [
                                        {
                                            'Action': 'UPSERT',
                                            'ResourceRecordSet': {
                                                'Name': elb.dns.record_name,
                                                'Type': 'A',
                                                'AliasTarget': {
                                                    'HostedZoneId': r53_hosted_zone_id,
                                                    'DNSName': load_balancer_dns,
                                                    'EvaluateTargetHealth': False
                                                }
                                            }
                                        }
                                    ]
                                })

                            print("updating route53 recordset: %s response: %s" % (elb.dns.record_name, change_resource_record_set_response.get("ResponseMetadata", {}).get("HTTPStatusCode")))

            if len([x for x in describe_services_response.get("services") if x.get("status") != "INACTIVE"]) > 0:
                # Update the service with the last revision of the task definition
                print "updating service: %s " % service.name
                update_service_response = ecs.update_service(
                    cluster=stack_name,
                    service=service.name,
                    taskDefinition=family,
                    desiredCount=service.desired_count,
                    deploymentConfiguration={
                        'maximumPercent': 200,
                        'minimumHealthyPercent': 50
                    }
                )

                print("update service_definition: %s response: %s" % (service.name, update_service_response.get("ResponseMetadata", {}).get("HTTPStatusCode")))

            else:
                # # Creating the service
                print "creating service: %s " % service.name
                create_service_response = ecs.create_service(
                    cluster=stack_name,
                    serviceName=service.name,
                    taskDefinition=family,
                    role="ecs-service-role" if len(load_balancers) > 0 else "",
                    desiredCount=service.desired_count,
                    deploymentConfiguration={
                        'maximumPercent': 200,
                        'minimumHealthyPercent': 50
                    },
                    loadBalancers=load_balancers,
                    placementStrategy=[service.placement_strategy.get("placement_strategy")] if service.placement_strategy is not None else [],
                    placementConstraints=[service.placement_strategy.get("placement_constraints")] if service.placement_strategy is not None else []

                )
                # pprint.pprint(create_service_response)
                print("service_definition: %s response: %s" % (service.name, create_service_response.get("ResponseMetadata", {}).get("HTTPStatusCode")))
        else:
            ecs.run_task(cluster=stack_name, taskDefinition=family, count=1)


# Shut everything down and delete task/service
def destroy_ecs_cluster(stack_name):

    list_services_response = ecs.list_services(cluster=stack_name)
    services = list_services_response["serviceArns"]

    while list_services_response.get("nextToken") is not None:
        list_services_response = ecs.list_services(cluster=stack_name, nextToken=list_services_response["nextToken"])
        services.extend(list_services_response["serviceArns"])

    for service in services:
        destroy_ecs_service(stack_name, service)


# delete the service including load balancers, and task definitions
def destroy_ecs_service(stack_name, service):

    print "deregistering service: %s" % service
    # search for attached load balancers
    describe_service_response = ecs.describe_services(cluster=stack_name, services=[service])

    load_balancer_arn = None
    target_group_arn = None
    listener_arn = None

    if len(describe_service_response["services"][0].get("loadBalancers", [])) > 0:
        target_group_arn = describe_service_response["services"][0]["loadBalancers"][0]["targetGroupArn"]
        describe_target_group_response = elbv2.describe_target_groups(TargetGroupArns=[target_group_arn])
        load_balancer_arn = describe_target_group_response["TargetGroups"][0]["LoadBalancerArns"][0]
        describe_listeners_response = elbv2.describe_listeners(LoadBalancerArn=load_balancer_arn)
        listener_arn = describe_listeners_response["Listeners"][0]["ListenerArn"]

    try:
        # Set desired service count to 0 (obligatory to delete)
        ecs.update_service(
            cluster=stack_name,
            service=service,
            desiredCount=0
        )
        # Delete service
        ecs.delete_service(
            cluster=stack_name,
            service=service
        )

    except:
        print("Service not found/not active")

    # terminate LB
    if load_balancer_arn is not None:
        elbv2.delete_listener(ListenerArn=listener_arn)
        elbv2.delete_target_group(TargetGroupArn=target_group_arn)
        elbv2.delete_load_balancer(LoadBalancerArn=load_balancer_arn)

    # List all task definitions and revisions
    task_definition_response = ecs.list_task_definition_families(familyPrefix="{}-{}".format(stack_name, service))
    tasks_definition_families = task_definition_response["families"]
    while task_definition_response.get("nextToken") is not None:
        task_definition_response = ecs.list_task_definition_families(next_token=task_definition_response["nextToken"])
        tasks_definition_families.extend(task_definition_response["families"])

    tasks_definitions = []
    for task_definition_family in tasks_definition_families:
        task_definition_response = ecs.list_task_definitions(familyPrefix=task_definition_family, status="ACTIVE")
        tasks_definitions.extend(task_definition_response["taskDefinitionArns"])
        while task_definition_response.get("nextToken") is not None:
            task_definition_response = ecs.list_task_definitions(next_token=task_definition_response["nextToken"])
            tasks_definitions.extend(task_definition_response["taskDefinitionArns"])

    # De-Register all task definitions
    for task_definition in tasks_definitions:
        ecs.deregister_task_definition(taskDefinition=task_definition)


# describe cluster services with its containers
def describe_ecs_cluster(stack_name):

    list_services_response = ecs.list_services(cluster=stack_name)
    services = list_services_response["serviceArns"]

    while list_services_response.get("nextToken") is not None:
        list_services_response = ecs.list_services(cluster=stack_name, nextToken=list_services_response["nextToken"])
        services.extend(list_services_response["serviceArns"])

    result = {
        "services": []
    }

    for service in services:
        result["services"].append(describe_ecs_service(stack_name, service))

    return result


# describe the service with its current task definitions
def describe_ecs_service(stack_name, service):

    # search for attached load balancers
    describe_service_response = ecs.describe_services(cluster=stack_name, services=[service])
    service_running_count = describe_service_response["services"][0].get("runningCount", 0)
    service_task_definition = describe_service_response["services"][0].get("taskDefinition", '')

    # List all task definitions and revisions
    task_definition_response = ecs.describe_task_definition(taskDefinition=service_task_definition)

    return {
        describe_service_response["services"][0].get("serviceName", 0): {
            "image": task_definition_response["taskDefinition"]["containerDefinitions"][0]["image"],
            "desired_count": service_running_count
        }
    }
