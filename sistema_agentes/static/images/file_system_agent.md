```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	prepare(prepare)
	react(react)
	__end__([<p>__end__</p>]):::last
	__start__ --> prepare;
	prepare --> react;
	react --> __end__;
	classDef default #fad7de
	classDef first #ffdfba
	classDef last #baffc9

```