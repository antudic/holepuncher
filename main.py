# run with: 
# prod: python main.py --fast --disable-openapi
# dev: python -m robyn main.py --dev

from robyn import Robyn, Request, jsonify
import asyncio, threading
import udp # local library


# mapping between key->endpoint
endpointDict = {}

# keep track of IPs to limit endpointDict entries
connections = set()

app = Robyn(__file__)


@app.get("/keyInfo")
async def query_get(req_obj: Request):
    global endpointDict

    if len(endpointDict) > 100_000:
        return "Server overload!"
    
    # check that key exists
    key = req_obj.query_params.get("key")
    if not key: return "No key supplied"
    if len(key) > 100: return "Key value too long"

    # make sure port is "valid"
    port = req_obj.query_params.get("port")
    if not port: return "No port supplied"
    if len(port) > 5: return "Port value too long"
    try: port = int(port)
    except (TypeError, ValueError): return "Invalid port"
    
    # if the key exists already
    if (endpoint := endpointDict.get(key)):

        if endpoint[0] == req_obj.ip_addr:
            return "No peer connected"
        
        else:
            connections.remove(endpoint[0])
            connections.add(req_obj.ip_addr)
            # ^ we make sure to add the new IP here, otherwise a malicious
            # actor could create infinite keys as long as they have 2 IPs

            endpointDict[key] = (req_obj.ip_addr, port)
            return jsonify(endpoint)
    
    # if the key, does not exist, we create it
    else:
        # first make sure that IP does not already active key
        if req_obj.ip_addr in connections:
            return "Key already exists"
            
        connections.add(req_obj.ip_addr)
        await timeoutKey(key) # this function is non-blocking
        endpointDict[key] = (req_obj.ip_addr, port)
        return "Key created"


@app.get("/delete")
async def query_get(req_obj: Request):
    # check that key exists
    key = req_obj.query_params.get("key")
    if not key: return "OK"
    if len(key) > 100: return "OK"

    try: connections.remove(endpointDict[key][0])
    except KeyError: pass

    try: del endpointDict[key]
    except KeyError: pass

    return "OK"


async def timeoutKey(key):
    
    async def realFunc(key):
        global endpointDict

        await asyncio.sleep(120)

        # make sure that the key is still first in the dictionary to make 
        # sure the key hasn't already been manually deleted and re-used
        if key == next(iter(endpointDict)):
            connections.remove(endpointDict[key][0])
            del endpointDict[key]

    loop = asyncio.get_event_loop()
    loop.create_task(realFunc(key))


threading.Thread(target=udp.main, daemon=True).start()

app.start(port=8080, host="0.0.0.0") 
