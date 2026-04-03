

# Start Docker

docker-compose down
docker-compose build
docker-compose up -d



to setup up tpm_dir on each node THIS IS A REQUIREMENT:

tpm_dir = /app/AnyLog-Network/tpm_dir/
system mkdir !tpm_dir

tell ori to set it up as a working directory in the deployment scripts



building from pycharm:
docker buildx build -f Dockerfile -t anylogco/anylog-network:tpm-test --load .

check with docker image ls

running containers:
cd docker-compose
make up EDGELAKE_TYPE=master
make up EDGELAKE_TYPE=operator
make attach EDGELAKE_TYPE=master
make attach EDGELAKE_TYPE=operator






# Anylog commands

id create keys where password = 123 and keys_file = tpm-192.168.86.29:8000/roy

id create keys for node where password = tpm-192.168.86.29:8000
id create keys for node where password = tpm-192.168.86.29:8000/

get public key where keys_file = tpm-192.168.86.29:8000/roy

get public key where keys_file = tpm-192.168.86.29:8000/node


<member = {"member" : {
    "id"   : "user_001",
    "type" : "user",
    "name"  : "node_test"
    }
}>
id sign !member where password = tpm-192.168.86.29:8000/
!member


<new_member = {"member" : {
    "id"   : "user_002",
    "type" : "user",
    "name"  : "roy"
    }
}>
id sign !new_member where key = tpm-192.168.86.29:8000/roy and password = 123
!new_member


id authenticate !member

id authenticate !new_member









# Secure Network 

use the new node management system

./multiple-instances/manage-instances.sh delete 1,2,3
./multiple-instances/manage-instances.sh stop 1,2,3
./multiple-instances/manage-instances.sh start 1,2,3

make sure to reset tpm_dir on each node

replace [#] with the node number and check other correct i
docker run -it \
  -e INIT_TYPE=prod \
  -e NODE_TYPE=master \
  -p 32349:32349 \
  -v "$(pwd)/multiple-instances/shared_dir_node[#]:/app/AnyLog-Network/tpm_dir" \
  --name anylog \
  --detach-keys=ctrl-d \
  --rm \
  anylogco/anylog-network:tpm-pp

tpm_dir = /app/AnyLog-Network/tpm_dir/

## ON OP 1
id create keys where password = 123 and keys_file = tpm-192.168.86.31:8001/root_key


<member = {"member" : {  
    "type" : "root",  
    "name"  : "rachel"  
    }  
}>

id sign !member where key = tpm-192.168.86.31:8001/root_key and password = 123

json !member

blockchain insert where policy = !member and local = true and master = !ledger_conn


id create keys for node where password = tpm-192.168.86.31:8001

<member = {"member" : {
    "id"   : "node_001",
    "type" : "node",
    "company"  : "Northern Light",
    "name" : "server south"
    }
}>

id sign !member where password = tpm-192.168.86.31:8001/

json !member

blockchain insert where policy = !member and local = true and master = !ledger_conn

## ON OP 2
id create keys for node where password = tpm-192.168.86.31:8001

<member = {"member" : {
    "id"   : "node_002",
    "type" : "node",
    "company"  : "Northern Light",
    "name" : "server north"
    }
}>

id sign !member where password = tpm-192.168.86.31:8001/

json !member

blockchain insert where policy = !member and local = true and master = !ledger_conn

## ON OP 1
id create keys where password = abc and keys_file = tpm-192.168.86.31:8001/roy


<member = {"member" : {
    "id"   : "user_001",
    "type" : "user",
    "name"  : "roy"
    }
}>

id sign !member where key = tpm-192.168.86.31:8001/roy and password = abc

json !member

blockchain insert where policy = !member and local = true and master = !ledger_conn



<permissions = {"permissions" : {
    "name" : "no restrictions",
    "databases" : ["*"],
    "enable" : ["*"]
    }
}>

id sign !permissions where key = tpm-192.168.86.31:8001/root_key and password = abc

json !permissions

blockchain insert where policy = !permissions and local = true  and master = !ledger_conn 



permission_id = blockchain get permissions where name = "no restrictions" bring ['permissions']['id']

member_user = blockchain get member where name = roy bring ['member']['public_key']

<assignment = {"assignment" : {
        "name" : "assignment to no restrictions",
        "permissions"  : !permission_id,
        "members"  : [!member_user]
        }
}>

id sign !assignment where key = tpm-192.168.86.31:8001/root_key and password = 123

json !assignment 

blockchain insert where policy = !assignment and local = true  and master = !ledger_conn  



<permissions = {"permissions" : {
    "name" : "node basic permissions",
    "databases" : ["*", "-lsl_demo"],
    "tables" : ["lsl_demo.temperature_sensor", "lsl_demo.ping_sensor"],
    "enable" : [ "file", "get", "reset", "sql", "echo", "print", "blockchain"],
    "disable" : ["get node id"]
    }
}>

id sign !permissions where key = tpm-192.168.86.31:8001/roy and password = 123

json !permissions

blockchain insert where policy = !permissions and local = true  and master = !ledger_conn 




member_node1 = blockchain get member where id = node_001 bring ['member']['public_key']
member_node2 = blockchain get member where id = node_002 bring ['member']['public_key']

permission_id =  blockchain get permissions where name = "node basic permissions" bring ['permissions']['id']

<assignment = {"assignment" : {
        "permissions"  : !permission_id,
        "members"  : [!member_node1, !member_node2]
        }
}>

id sign !assignment where key = tpm-192.168.86.31:8001/roy and password = 123

json !assignment 

blockchain insert where policy = !assignment and local = true  and master = !ledger_conn  


## ON OP 1
set local password = 123
## ON OP 2
set local password = 456


## ON MASTER
id create keys for node where password = tpm-192.168.86.31:8001/

<member = {"member" : {  
    "type" : "node",  
    "name"  : "master_node"  
    }  
}>  

id sign !member where password = tpm-192.168.86.31:8001/

json !member

blockchain insert where policy = !member and local = true and master = !ledger_conn

## ON OP 1
<permissions = {"permissions" : {
    "name" : "master node permissions",
    "enable" : [ "file", "event", "echo", "print"]
    }
}>

id sign !permissions where key = tpm-192.168.86.31:8001/roy and password = 123

json !permissions

blockchain insert where policy = !permissions and local = true  and master = !ledger_conn 


permission_id = blockchain get permissions where name = "master node permissions" bring ['permissions']['id']
member_node = blockchain get member where name = master_node bring ['member']['public_key']

<assignment = {"assignment" : {
        "name" : "master assignment",
        "permissions"  : !permission_id,
        "members"  : [!member_node]
        }
}>

id sign !assignment where key = tpm-192.168.86.31:8001/roy and password = 123

json !assignment 

blockchain insert where policy = !assignment and local = true  and master = !ledger_conn  


## ON MASTER
set local password = masterlocpsswd

## ON ALL 

tpm set where conn = 192.168.86.31:8001

tpm enabled = on

tpm get info

set node authentication on






# Setup
./multiple-instances/setup-multiple-instances.sh 3
docker-compose -f multiple-instances/docker-compose.instances.yaml up -d

./multiple-nodes/manage-anylog-nodes.sh setup 1 master 2 operator 

# go into pp-dev branch of Anylog-Network and run just this:
docker build -f Dockerfile -t anylogco/anylog-network:tpm-pp .

./multiple-nodes/manage-anylog-nodes.sh start

<!-- open 3 terminals one for each node -->
./multiple-nodes/manage-anylog-nodes.sh attach master 1
./multiple-nodes/manage-anylog-nodes.sh attach operator 1
./multiple-nodes/manage-anylog-nodes.sh attach operator 2

in each node, run the following commands:
tpm_dir = /app/AnyLog-Network/tpm_dir/
enable_tpm = "true"
tpm_ip = 192.168.86.31
tpm_port = 8001



