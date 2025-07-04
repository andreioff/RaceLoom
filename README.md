# RaceLoom

_A command-line tool for detecting, analysing, and illustrating harmful race conditions in Software-Defined Networks (SDNs) via symbolic traces._

---

## 📖 Overview

**RaceLoom** is a Python 3 command-line tool for detecting harmful race conditions in Software-Defined Networks (SDNs) using forwarding properties. It combines:

1. [DyNetKAT](https://arxiv.org/abs/2102.10035), a domain-specific language for modeling SDNs, and [Maude 3.5](https://github.com/maude-lang/Maude/tree/Maude3.5), a high-performance rewriting logic system, to extract symbolic execution traces from a given network model
2. [KATch](https://github.com/cornell-netlab/KATch), a fast symbolic verifier for NetKAT, to check potentially harmful concurrent events against NetKAT forwarding properties

Given a DyNetKAT network model, a set of forwarding properties, and a trace depth, RaceLoom generates all possible execution traces up to the specified depth, identifies pairs of network events that may occur concurrently, checks them against the properties, and reports any violating traces.

---

## ⚙️ Prerequisites

1. **Python**: 3.12.8 or higher
2. **Java Runtime**: 8 or higher
3. **Virtual environment**: optional, but recommended

To create and activate a new virtual environment, run:

```bash
python3 -m venv venv
source venv/bin/activate
```

## 🚀 Installation

Clone the repository and install the tool using `pip`:

```bash
git clone https://github.com/andreioff/RaceLoom.git
cd RaceLoom
pip install .
```

then, test the _KATch_ executable:

```bash
./bin/katch/test_katch.sh
# should output "OK!"
```

## 🧰 Usage

Once installed, the tool can be executed via the command line:

```
python3 main.py [-h] [-d DEPTH] [-t THREADS] [-v] [-s {dfs,bfs,pbfs}] sdnModelFilePath forwardingPropsFilePath

positional arguments:
  sdnModelFilePath
  forwardingPropsFilePath

options:
  -h, --help            show this help message and exit
  -d DEPTH, --depth DEPTH
                        Depth of search (default is 5)
  -t THREADS, --threads THREADS
                        Number of threads to use when generating traces (only used for the 'pbfs' generation strategy)
  -v, --verbose         Print log messages during execution (only supported by some generation strategies)
  -s {dfs,bfs,pbfs}, --strategy {dfs,bfs,pbfs}
                        Strategy used to generate the traces (default is 'bfs')
```

### 🔧 Example

```bash
python3 main.py -d 10 -t 5 -s pbfs -v ./examples/firewall/firewall.json ./examples/firewall/forwarding_props.json
```

### NetKAT and DyNetKAT encoding

> [!IMPORTANT]
> For NetKAT expressions: - The `dup` operator is forbidden - Packet field values can only be integers
>
> For DyNetKAT expressions: - The parallel operator `||`is forbidden

For [NetKAT](https://netkat.org/) expressions, the following syntax rules apply:

- The predicate for dropping a packet ($0$) is encoded as `zero`.
- The predicate for forwarding a packet without any modifications ($1$) is encoded as `one`.
- The test predicate ($=$) which checks if a field `arg1` of the current packet has the value `arg2` is encoded as `arg1 = arg2`.
- The negation operator ($\neg$) is only supported as negated tests, encoded:`arg1 != args2`, which checks if a packet field `arg1` does not have the value `arg2`.
- The modification operator ($\leftarrow$) which assigns the value `arg2` to a field `arg1` in the current packet is encoded as `arg1 <- arg2`.
- The union (and disjunction) operator ($+$) is encoded as `arg1 + arg2`
- The sequential composition (and conjunction) operator ($\cdot$) is encoded as `arg1 . arg2`
- The Kleene star operator ($*$) is encoded as `arg1*`

For **DyNetKAT** expressions, the following syntax rules apply:

- The dummy policy ($\bot$) is encoded as `bot`.
- The sequential composition operator ($;$) is encoded as `arg1 ; arg2`. `arg1` can either be a NetKAT policy or a communication term and `arg2` must always be a DyNetKAT term.
- The communication operators for sending ($!$) and receiving ($?$) are encoded as `arg1 ! arg2` and `arg1 ? arg2`, respectively. Here, `arg1` is a channel name and `arg2` is a NetKAT policy.
- The non-deterministic choice operator ($\oplus$) is encoded as `arg1 o+ arg2`.
- Recursive variables are explicitly defined in the file that is given as input to the tool.
- Any NetKAT policy must be surrounded by quotation marks (`" "`).

> [!NOTE]
> Due to how the sequential composition operator is defined, an expression sequentially composing multiple terms in a row must be explicitly separated with parentheses. E.g. the DyNetKAT expression `(Up ! "zero") ; "one" ; (Up ! "zero") ; bot` must be specified as `(Up ! "zero") ; ("one" ; ((Up ! "zero") ; bot))`.

### SDN model format

The SDN model is provided to RaceLoom as a `JSON` file with the following structure:

```
{
  "Switches": {
    "SW1": {
      "InitialFlowTable": "<NetKAT expression>",  // Optional
      "DirectUpdates": [
        {
          "Channel": "<string>",
          "Policy": "<NetKAT expression>",
        }
        ...
      ],
      "RequestedUpdates": [
		    {
          "RequestChannel": "<string>",
          "RequestPolicy": "<NetKAT expression>",
          "ResponseChannel": "<string>",
          "ResponsePolicy": "<NetKAT expression>",
        },
        ...
      ]
    },
    ...
  },
  "Links": "<NetKAT expression>",  // Optional
  "RecursiveVariables": {
    "C1": "<DyNetKAT expression>",
    ...
  },
  "OtherChannels": ["<string>", ...],
  "Controllers": ["C1", ...]
}
```

The meaning of each key is as follows:

- `Switches` contains information about every switch in the SDN. The dictionary maps switch names to flow table and update information, which include:

  - `InitialFlowTable` - optional field for specifying the flow table of the switch before any updates as a NetKAT expression. If excluded, the default value is `zero`.
  - `DirectUpdates` - new flow table expressions received by the switch at any time. Each update consists of a NetKAT `Policy` received on a `Channel`.
  - `RequestedUpdates` - new flow table expressions that the switch should request from the controller. The switch can request an update by sending a `RequestPolicy` on a `RequestChannel` to the controller, then waits for the `ResponsePolicy` on a `ResponseChannel`.

  Internally, this dictionary is concatenated into a single DyNetKAT expression called _Big Switch_. More details are provided in the next section.

- `Links` - a NetKAT expression encoding packet forwarding over all links in the SDN topology. E.g. the NetKAT expression `(port = 1) . (port <- 3) + (port = 2) . (port <- 4)` encodes 2 links: one forwarding packets from port 1 to port 3, and the other forwarding packets form port 2 to port 4.
- `RecursiveVariables` - variables assigned to arbitrary DyNetKAT expressions. These are used to model controller actions. Usually, these variables are recursive, i.e. after a series of actions they return to their initial behavior, e.g. the expression `C1: "(Up ! \"zero\") ; C1"` defines a variable `C1` that recursively sends policy `"zero"` over channel `Up`
- `OtherChannels` - list of channels not specified in the `Switches` dictionary that are used between controllers/recursive variables
- `Controllers` - a list of recursive variable names that define the behavior of different controllers. E.g. the list `["C1", "C2"]` means that the behavior specified by variable `C1` should be used as the first controller and the behavior specified by variable `C2` should be used as the second controller.

**Examples** of SDN models can be found in `./examples`.

#### Model conversion

Internally, the SDN information provided in the JSON file is converted into DyNetKAT expressions.

The expressions of the `RecursiveVariables` are used as is, without any modifications.

The `Switches` dictionary and the `Links` expression are combined into a single _Big Switch_ that behaves as follows:

- At any point in time, the big switch can non-deterministically choose to:
  1.  Forward packets
  2.  Receive direct updates for one of its inner switches
  3.  Request updates for one of its inner switches to a controller
- The forwarding policy of the big switch is a NetKAT expression concatenating all flow tables of the inner switches and the topology links: $(X_1, \ldots, X_n) \cdot Links \cdot ((X_1, \ldots, X_n) \cdot Links)^*$, where $X_1, \dots, X_n$ are the flow table expressions of the inner switches. Intuitively, this policy encodes the forwarding of a packet throughout the network one or more time. At every step, the packet is forwarded according to the flow table of an inner switch and a topology link.
- Whenever an update of an inner switch occurs (direct or requested update), the flow table of the inner switch is replaced entirely with the new NetKAT expression received. E.g. if the big switch is composed of 2 switches, it forwards packets according to the expression: $((X_1 + X_2) \cdot Links) \cdot ((X_1 + X_2) \cdot Links)^* $. After an update of the second inner switch to policy $N_2$, the big switch will forward packets according to the expression: $((X_1 + N_2) \cdot Links) \cdot ((X_1 + N_2) \cdot Links)^\* $.
- Whenever an update is requested by the big switch from a controller, no other update can be requested until a response is received for the current request. Forwarding packets or receiving direct updates may still occur while the big switch waits for a response.

The behavior of the SDN is encoded as the parallel composition between the constructed _Big Switch_ and the controller variables specified in the `Controllers` array:

```math
BigSwitch \| C1 \| C2 \| ...
```

### Forwarding properties format

The forwarding properties are provided to RaceLoom as a `JSON` file with the following structure:

```
{
  "Properties": {
    "CT->SW": { // optional
      "Expression": "<NetKAT expression>",
      "AllowsPackets": true | false
    },
    "CT->SW<-CT": { // optional
      "Expression": "<NetKAT expression>",
      "AllowsPackets": true | false
    },
    "CT->CT->SW": { // optional
      "Expression": "<NetKAT expression>",
      "AllowsPackets": true | false
    }
  }
}
```

One forwarding property can be specified for every type of race condition. RaceLoom distinguishes between 3 types of race conditions:

- `CT->SW` - occurs between forwarding events of a switch _SW_ and reconfiguration events from controllers to _SW_.
- `CT->SW<-CT` - occurs between reconfiguration events of 2 controllers targeting the same switch.
- `CT->CT->SW` - occurs between reconfiguration events of 2 controllers: _C1_ and _C2_, where _C2_ reconfigures _C1_ and _C1_ reconfigures a switch.
  If a forwarding property is not specified for a particular type of race, then the tool will skip all such races.

Intuitively, if a race condition occurs, we say it is _harmful_ if it affects the packet forwarding behavior of the SDN. This means that evaluating an SDN against a forwarding property has different outcomes before and after the race condition happened. Thus, a forwarding property is an arbitrary NetKAT expression that encodes what packets are allowed/not allowed to be forwarded by the SDN model when a race condition occurs. In the `JSON` file, this is specified as an object with 2 keys, where:

- `Expression` maps to the NetKAT expression.
- `AllowsPackets` is a boolean flag that dictates the condition under which the forwarding property holds. When `false`, the tool checks if the `Expression` is equivalent to 0 (no packets are forwarded), and when `true`, the tool checks if the `Expression` is **not** equivalent to 0 (some packets are forwarded).
  The forwarding policy of the SDN can be referred inside the property expressions through the special term `@Network`. For example, the property:

```
{
  "Expression": "(port = 1 + port = 2) . @Network . (port = 3 + port = 4)",
  "AllowsPackets": true
}
```

holds when at least one packet entering the SDN on port 1 or 2 can be forwarded by the network to port 3 or 4.

### Output

RaceLoom will output any results in a folder: `./output` of the following structure:

```
├── output/
│   ├── run_<date>T<time>/
│       ...
│   └── final_stats.csv
```

A separate folder within the output folder is made for every execution of RaceLoom, which contains traces showcasing harmful race conditions found by the tool (if any). The traces are saved twice: once in `DOT` format, and once as text files containing the generated trace, the type of race condition found, and the concurrent transitions that define the race. The `DOT` files can be converted into images using a `DOT` rendering tool.

The `final_stats.csv` file contains various statistics about all executions of the tool, such as input file names, execution times, amount of cache hits and misses etc.

## 🔗 Third-Party Dependency

This application relies on a Java-based NetKAT verification tool. The `jar` file is included in the repository at:

```bash
./bin/katch/KATch-assembly-0.1.0-SNAPSHOT.jar
```

and it is executed through the script:

```bash
./bin/katch/katch.sh
```

You do not need to install this manually or specify the script path anywhere. RaceLoom invokes it automatically. However, `Java` must be installed and available in your system's `PATH`.

## 🧪 Running Tests

This project uses [pytest 8.4.1](https://pypi.org/project/pytest/8.4.1/) for testing.

Install the test dependencies using:

```bash
pip install .[test]
```

To run the tests, from the main directory of the repository execute:

```bash
pytest
```

## ⚠️ Known Issues / Limitations

- Syntax of NetKAT expressions is validated by KATch, which happens after RaceLoom generated the symbolic traces. As a result, NetKAT syntax errors may cause the tool to crash during the trace analysis step.
  - This also means that no checks are done for the format or operators used in the NetKAT expressions. **NOTE!:** the tool expects NetKAT $^{-dup}$ expressions, i.e. NetKAT policies that do not contain the `dup` operator.
- Syntax of DyNetKAT expressions is not extensively validated. If any of the forbidden operators are used, a Maude error will occur.
- In some cases, syntax errors thrown by Maude do not stop the execution of RaceLoom. If any such errors are displayed at the beginning of the tool execution, **the final output is not reliable**. In that case, the DyNetKAT expressions of the input SDN must be fixed and the tool must be run again.
- Trace generation can be (very) slow for complex DyNetKAT models that use a lot of SDN elements, i.e. controllers or big switches, or non-deterministic choices. Non-deterministic choices are introduced by either explicitly using them in controller expressions, or by using big switches with a lot of updates. For reference, generating traces for an SDN consisting of 3 recursive elements running in parallel with 1, 1, and 21 non-deterministic branches, respectively, can take up to 42 minutes.

## 📄 License

This project is licensed under the **MIT License**.
See the LICENSE file for more details.
