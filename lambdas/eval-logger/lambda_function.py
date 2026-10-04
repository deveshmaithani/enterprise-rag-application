import os
import datetime
import boto3
import pg8000.native

cloudwatch = boto3.client("cloudwatch")


def get_average_score(evaluator_name, run_id, service_name):
    response = cloudwatch.get_metric_data(
        MetricDataQueries=[
            {
                "Id": "score",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "Bedrock-AgentCore/Evaluations",
                        "MetricName": evaluator_name,
                        "Dimensions": [
                            {"Name": "service.name", "Value": service_name},
                            {
                                "Name": "evaluationJobId",
                                "Value": f"arn:aws:bedrock-agentcore:us-east-1:497012402349:batch-evaluate/{run_id}",
                            },
                        ],
                    },
                    "Period": 86400,
                    "Stat": "Average",
                },
            }
        ],
        StartTime=datetime.datetime(2020, 1, 1),
        EndTime=datetime.datetime.utcnow(),
    )

    values = response["MetricDataResults"][0]["Values"]
    return values[0] if values else None


def lambda_handler(event, context):
    run_id = event["run_id"]
    config_label = event["config_label"]
    service_name = event["service_name"]

    faithfulness = get_average_score("Builtin.Faithfulness", run_id, service_name)
    relevance = get_average_score("Builtin.ResponseRelevance", run_id, service_name)
    correctness = get_average_score("Builtin.Correctness", run_id, service_name)

    conn = pg8000.native.Connection(
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_NAME"],
    )

    conn.run(
        """
        INSERT INTO eval_runs
            (config_label, faithfulness, answer_relevance, context_precision)
        VALUES
            (:label, :faithfulness, :relevance, :correctness)
        """,
        label=config_label,
        faithfulness=faithfulness,
        relevance=relevance,
        correctness=correctness,
    )
    conn.close()

    return {
        "status": "logged",
        "faithfulness": faithfulness,
        "relevance": relevance,
        "correctness": correctness,
    }
