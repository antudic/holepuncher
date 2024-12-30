# run with: 
# prod: python main.py --fast --disable-openapi
# dev: python -m robyn main.py --dev

from robyn import Robyn, Request, jsonify
import time, asyncio, threading
import udp # local library

# this keeps track of the keyInfo's
signalingDict = {}

# this keeps track of which IPs have keyInfo's to limit one IP to one key
connections = set()

app = Robyn(__file__)


class keyInfoEnum:
    CREATED_AT = 0
    CLIENT_ONE = 1
    CLIENT_TWO = 2

    IP = 0
    PORT = 1


@app.get("/delete")
async def query_get(req_obj: Request):
    # check that key exists
    key = req_obj.query_params.get("key")

    # delete connection (so machine can once again make a new key)
    try: connections.remove(signalingDict[key][keyInfoEnum.CLIENT_ONE][keyInfoEnum.IP])
    except KeyError: pass

    # delete the keyInfo
    try: del signalingDict[key]
    except KeyError: pass

    return "OK."


@app.get("/keyInfo")
async def query_get(req_obj: Request):

    if len(connections) > 100_000:
        return "Server overload!"

    # check that key exists
    key = req_obj.query_params.get("key")
    if not key: return "No key supplied."
    if len(key) > 100: return "Key value too long"

    # get the client IP
    clientIP = req_obj.ip_addr

    # if the key exists already
    if (keyInfo := signalingDict.get(key)):

        # if we have keyInfo for client two, send back key info
        if keyInfo[keyInfoEnum.CLIENT_TWO]:
            return jsonify(keyInfo[1:])
        
        # if we don't have keyInfo for client two and client one sends the request
        elif clientIP == keyInfo[keyInfoEnum.CLIENT_ONE][keyInfoEnum.IP]:
            return "No peer connected."
        
        # at this point we know client two sent the request and that we need to write it down
        else:
            # make sure port is "valid"
            port = req_obj.query_params.get("port")
            if not port: return "No port supplied."
            if len(port) > 5: return "Port value too long"

            # update keyInfo data for client two
            keyInfo[keyInfoEnum.CLIENT_TWO] = (clientIP, port)

            return jsonify(keyInfo[1:])

    else:
        # first check if IP already has room active
        if clientIP in connections: return "You already have an active room!"

        # make sure port is "valid"
        port = req_obj.query_params.get("port")
        if not port: return "No port supplied."
        if len(port) > 5: return "Port value too long"

        createdAt = int(time.time())

        signalingDict[key] = [
            createdAt,        # CREATED_AT
            (clientIP, port), # CLIENT_ONE
            None              # CLIENT_TWO
            ]
        
        await keyInfoTimeout(createdAt, key) # non-blocking

        return "Key created."


async def keyInfoTimeout(key, createdAt):
    
    async def realFunc(key, createdAt):
        await asyncio.sleep(200) # sleep for 200 seconds

        # since we are now in the future, get the potentially new keyInfo 
        try: keyInfo = signalingDict[key]
        except KeyError: return # if they key no longer exists, all work is done

        if keyInfo[keyInfoEnum.CREATED_AT] == createdAt:
            # this ensures that it's not a new room with the same key
            
            try: connections.remove(keyInfo[keyInfoEnum.CLIENT_ONE][keyInfoEnum.IP])
            except KeyError: pass

            try: del signalingDict[key]
            except KeyError: pass

    loop = asyncio.get_event_loop()
    loop.create_task(realFunc(key, createdAt))


threading.Thread(target=udp.main, daemon=True).start()

app.start(port=8080, host="0.0.0.0") 
