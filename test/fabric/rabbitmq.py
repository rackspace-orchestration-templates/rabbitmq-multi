
import random
import string
from kombu import Connection
from fabric.api import env, task
from envassert import detect, file, group, package, port, process, user
from envassert import service
from hot.utils.test import get_artifacts


def random_string(size=16, chars=string.ascii_lowercase+string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def amqp_works(login, password, host):
    """
    Submits a random string message payload to an amqp server, retrieves it,
    and verifies that the received payload matches the sent
    """
    conn_string = 'amqp://{}:{}@{}:5672//'.format(login, password, host)
    print "connection string is {}".format(conn_string)

    test_queue_name = 'test_queue_'+random_string()
    test_payload = random_string(128)

    with Connection(conn_string) as conn:
        print "* connecting to {}".format(host)
        conn.connect()
        simple_queue = conn.SimpleQueue(test_queue_name)
        print "* sending payload:\n {}".format(test_payload)
        simple_queue.put(test_payload)
        print "* payload sent. Disconnecting."
        simple_queue.close()

    with Connection(conn_string) as conn:
        print "* connecting to {}".format(host)
        conn.connect()
        simple_queue = conn.SimpleQueue(test_queue_name)
        print "* retrieving payload..."
        message = simple_queue.get(block=True, timeout=5)
        print "* got payload:\n {}".format(message.payload)
        message.ack()
        print "* payload received. Disconnecting."
        return message.payload == test_payload


@task
def check():
    env.platform_family = detect.detect()

    for pkg in ["rabbitmq-server",
                "python-pip",
                "curl",
                "unzip",
                "supervisor",
                "dnsmasq"]:
        assert package.installed(pkg), \
            "package {} is not installed".format(pkg)

    for path in ["/var/lib/rabbitmq/.erlang.cookie",
                 "/etc/supervisor/conf.d/consul.conf",
                 "/usr/local/lib/supervisor/start_consul.sh",
                 "/etc/dnsmasq.d/consul_dns.conf"]:
        assert file.exists(path), "file {} does not exist".format(path)

    assert port.is_listening(5672), "port 5672 (RabbitMQ) is not listening"
    assert user.exists("rabbitmq"), "there is no rabbitmq user"
    assert group.is_exists("rabbitmq"), "there is no rabbitmq group"
    assert process.is_up("supervisord"), "supervisord is not running"
    assert process.is_up("consul"), "consul is not running"
    assert process.is_up("epmd"), "epmd is not running"
    assert process.is_up("beam.smp"), "beam.smp is not running"
    assert process.is_up("dnsmasq"), "dnsmasq is not running"
    assert service.is_enabled("rabbitmq-server"), "nginx is not enabled"
    assert service.is_enabled("supervisor"), "supervisor is not enabled"
    assert amqp_works(env.amqp_login, env.amqp_password, env.host), \
        "RabbitMQ did not respond as expected"


@task
def artifacts():
    env.platform_family = detect.detect()
    get_artifacts()
