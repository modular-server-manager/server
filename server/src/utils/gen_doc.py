from ..bus.events import Events, Event

event_md_template = """
## {name} ({id})

{description}

### Arguments: 

| Name | Type | ID |
|------|------|----|
{arguments}

### Returns:

{return_type}
"""

# as a table
arg_row_md_template = "| {name} | {type} | {id:#05d} |"

def generate_event_md(event : Event) -> str:
    arguments_md = ""
    for arg in event.args:
        arguments_md += arg_row_md_template.format(name=arg.name, type=arg.type, id=arg.id) + "\n"
    return event_md_template.format(
        name=event.name,
        id=hex(event.id),
        description=event.description if event.description else "No description available.",
        arguments=arguments_md if arguments_md else "| None | None | None |",
        return_type=event.return_type if event.return_type else "None"
    )
    

def main():
    with open("EVENTS.md", "w") as f:
        f.write("# Events\n\n")
        for event in Events.events.values():
            f.write(generate_event_md(event))
            f.write("\n---\n")