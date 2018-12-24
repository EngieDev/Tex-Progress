from http.server import BaseHTTPRequestHandler, HTTPServer
import threading, json, sys, time, datetime, re, hashlib
import subprocess

# Logs message for webserver and prints to console
def logger(m):
    m = datetime.datetime.now().strftime("%H:%M") + " " + m
    print(m)
    logLock.acquire()
    log.append(m)
    logLock.release()

# Processes the data for the chartjs api
def dataProcess():
    dataLock.acquire()
    d = data["data"]
    dataLock.release()

    chartData = {}
    timestamps = []

    for timestamp in d.keys():
        time = timestamp

        record = d[timestamp]
        timestamps.append(timestamp)

        for id in record.keys():
            if id == "totals":
                continue

            if id not in chartData:
                chartData[id] = {}
                if len(timestamps) == 1:
                    chartData[id]["values"] = []
                else:
                    chartData[id]["values"] = [0] * (len(timestamps)-1)
                    # Instantiates zero array of same length of timestamp


            if "name" in record[id].keys():
                chartData[id]["name"] = record[id]["name"]

            if id == "_top_":
                chartData[id]["name"] = "_top_"

            chartData[id]["values"].append(int(record[id]["total"])+int(record[id]["headers"]))

        # Adds 0 for each remaining key
        for id in chartData.keys():
            if id not in record.keys():
                chartData[id]["values"].append(0)

    return json.dumps({"data": chartData, "timestamps": timestamps})

# Thread for running server
class serverThread(threading.Thread):
    def run(self):
        try:
            # Starts webserver
            dataLock.acquire()
            self.server = HTTPServer(('', data["settings"]["port"]), serverHandler)
            logger('Started httpserver on port ' + str(data["settings"]["port"]))
            dataLock.release()
            self.server.serve_forever()
        except Exception as e:
            print("An error occured starting webserver:")
            print(e)

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server = None
            print("Shut down webserver")

# Handles the requests
class serverHandler(BaseHTTPRequestHandler):
    # GET requests
    def do_GET(self):
        status=200

        # Checks url matches file
        if self.path == "/":
            contentType="text/html"
            content=open("static/index.html").read()
        elif self.path == "/static/chart.bundle.min.js":
            contentType="text/js"
            content=open("static/chart.bundle.min.js").read()
        elif self.path == "/static/jquery-3.3.1.min.js":
            contentType="text/js"
            content=open("static/jquery-3.3.1.min.js").read()
        elif self.path == "/static/script.js":
            contentType="text/js"
            content=open("static/script.js").read()
        elif self.path == "/static/style.css":
            contentType="text/css"
            content=open("static/style.css").read()
        elif self.path == "/static/moment.js":
            contentType="text/js"
            content=open("static/moment.js").read()
        elif self.path == "/api/settings/":
            contentType="text/json"
            dataLock.acquire()
            content=json.dumps(data["settings"])
            dataLock.release()
        elif self.path == "/api/log/":
            contentType="text/json"
            logLock.acquire()
            content=json.dumps(log)
            logLock.release()
        elif self.path == "/api/data/":
            contentType="text/json"
            content = dataProcess()
        else:
            status=404
            contentType="text/plain"
            content="404 Not Found"

        # Sends html response
        self.send_response(status)
        self.send_header('Content-type', contentType)
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))
        return

    # POST requests
    def do_POST(self):
        # Saves settings from form
        if self.path == "/api/settings/":
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write("1".encode("utf-8"))
            try:
                s = self.rfile.read(int(self.headers['Content-Length']))
                s = json.loads(s)

                dataLock.acquire()
                data["settings"]["texFile"] = s["texFile"]
                data["settings"]["period"] = s["period"]
                data["settings"]["port"] = int(s["port"])
                dataLock.release()

                dataFile = open(file, "w+")
                dataLock.acquire()
                dataFile.write(json.dumps(data))
                dataLock.release()
                dataFile.close()
                logger("Saved settings - A restart is required if port has been changed.")
            except Exception as e:
                logger("Failed to save: " + str(e))
            return
        return

# Dictionary to store all data, settings and log data
data = {
    "settings": {
        "port": 8090,
        "texFile": "",
        "period": 60
        },
    "data": {},
    "identifiers": [], # Used for detecting past sections
    "hash": "" # Used to check for texcount changes in output
}
log = []

# lock for conccurrent data access
dataLock = threading.Lock()
logLock = threading.Lock()

if __name__ == '__main__':
    # Loads the data file, or creates new one depending on flags given
    if len(sys.argv) == 1:
        logger("No file argument given")
        sys.exit()

    file = sys.argv[1]

    if file == "new":
        if len(sys.argv) != 5:
            logger("Invalid arguments: main.py new [json] [port] [texFile]")
            sys.exit(0)

        file = sys.argv[2]
        port = int(sys.argv[3])
        texFile = sys.argv[4]

        data["settings"]["port"] = port
        data["settings"]["texFile"] = texFile

        logger("Creating new data file")

        # Checks file exists
        try:
            fh = open(file, 'r')
            logger("File already exists")
            sys.exit()
        except FileNotFoundError:
            pass
        dataFile = open(file, "w+")
        dataLock.acquire()
        dataFile.write(json.dumps(data))
        dataLock.release()
        dataFile.close()

    logger("Loading data")
    try:
        data = json.loads(open(file).read())
    except Exception as e:
        logger("Loading of file failed")
        logger(str(e))
        sys.exit()
    logger("Data loaded")

    # Checks for perl:
    result = subprocess.run(['perl', 'texcount.pl'], stdout=subprocess.PIPE)
    if re.match("TeXcount version", result.stdout.decode("utf-8")) is None:
        print("Error with perl or missing texcount.pl script:")
        print(result.stdout)
        sys.exit(2)

    # Starts server in background
    serv = serverThread()
    serv.start()

    # Starts monitoring the tex file
    while True:
        try:
            result = subprocess.run(['perl', 'texcount.pl', data["settings"]["texFile"]], stdout=subprocess.PIPE)
            texCount = result.stdout.decode("utf-8")

            # Gets sleep time
            dataLock.acquire()
            sleep = float(data["settings"]["period"])
            dataLock.release()

            if re.search("File not found", texCount) is not None:
                logger("Failed to find tex file, invalid perms?")
                time.sleep(sleep)
                continue

            # Checks for changes, saves data storage and makes graph neater:
            hash = hashlib.sha1(texCount.encode("utf-8")).hexdigest()
            if hash == data["hash"]:
                time.sleep(sleep)
                continue

            # Gets timestamp
            timestamp = str(int(time.time()))

            # Parses outpout into dataset
            textWords = re.search("Words in text: (\d+)", texCount).group(1)
            headerWords = re.search("Words in headers: (\d+)", texCount).group(1)
            extraWords = re.search("Words outside text \(captions, etc.\): (\d+)", texCount).group(1)

            dataset = {"totals": {"total": int(textWords),
                                  "headers": int(headerWords),
                                  "captions": int(extraWords)
                                  }
                       }

            ids = []

            # Checks for subcount, if not found sub in _top_ and skip rest of checkss
            if re.search("Subcounts:", texCount) is None:
                dataset["_top_"] = {"total": int(textWords),
                                    "headers": int(headerWords),
                                    "captions": int(extraWords)
                                    }
            else:
                # Grabs the top subcount as it doesn't follow normol patterns:
                subcount = re.search("(\d+)\+(\d+)\+(\d+) \W+\d+/\d+/\d+/\d+\) _top_", texCount)
                dataset["_top_"] = {"total": int(subcount.group(1)),
                                    "headers": int(subcount.group(2)),
                                    "captions": int(subcount.group(3))
                                    }

                # Grabs the breakdown
                regex = re.finditer("(\d+)\+(\d+)\+(\d+) \W+\d+/\d+/\d+/\d+\)\W+(.*):(.*)", texCount)

                # Creates unique identifier
                part = ""
                chapter = ""
                section = ""
                subsection = ""

                # Duplicates past identifiers
                dataLock.acquire()
                pastIDs = data["identifiers"]
                dataLock.release()

                for match in regex:
                    if match.group(4) == "Part":
                        part = match.group(5)
                        chapter = section = subsection = ""
                    elif match.group(4) == "Chapter":
                        chapter = match.group(5)
                        section = subsection = ""
                    elif match.group(4) == "Section":
                        section = match.group(5)
                        subsection = ""
                    elif match.group(4) == "Subsection":
                        subsection = match.group(5)

                    id = part + "//" + chapter + "//" + section + "//" + subsection

                    dataset[id] = {"total": int(match.group(1)),
                                   "headers": int(match.group(2)),
                                   "captions": int(match.group(3)),
                                   "name": match.group(5)
                                   }

                    ids.append(id)
                    if id in pastIDs:
                        pastIDs.remove(id)

                # Sets all remaining pastids to 0
                for id in pastIDs:
                    dataset[id] = {"total": 0,
                                   "headers": 0,
                                   "captions": 0
                                   }

            dataLock.acquire()
            data["identifiers"] = ids
            data["data"][timestamp] = dataset
            data["hash"] = hash
            dataLock.release()

            dataFile = open(file, "w+")
            dataLock.acquire()
            dataFile.write(json.dumps(data))
            dataLock.release()
            dataFile.close()

            time.sleep(sleep)
        except KeyboardInterrupt:
            logger("Closing down")
            serv.stop()
            sys.exit(1)
        except Exception as e:
            print("Error:")
            print(e)
            serv.stop()
            sys.exit(0)
