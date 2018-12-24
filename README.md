# Tex Progress
Charts latex file progress in a browser using texcount as the backend

![Example Chart](.github/example_chart.png?raw=true "Example Chart")

## Requirements
 - perl - StrawberryPerl, ActivePerl etc
 - python3


## Usage
To start a new instance:
 - `python main.py new [json] [port] [texFile]`

    i.e: `python main.py new data.json 8090 essay.tex`
 - Open up the browser to [localhost:8090](http://localhost:8090) (sub in port chosen)

To continue an existing instance:
 - `python main.py [json]`
