import os.path
import json
import sys

from .bus.events import Events, Event

__FILE_DIR__ = os.path.dirname(__file__)

event_md_template = """
## {id:#05d} - {name}

{description}

### Arguments: 

| Name | Type | ID | Description |
|------|------|----|-------------|
{arguments}

### Returns:

`{return_type}` : {return_description}
"""

arg_row_md_template = "| {name} | `{type}` | {id:#03d} | {description} |"


def load_event_descriptions() -> dict[str, dict[str, str|dict[str, str]]]:
    with open(f"{__FILE_DIR__}/events_descriptions.json", "r") as f:
        return json.load(f)


def generate_event_md(event : Event, event_desc : str, args_descs : dict[str, str], return_desc : str) -> str:
    arguments_md = ""
    for arg in event.args:
        arguments_md += arg_row_md_template.format(
            name=arg.name,
            type=arg.type,
            id=arg.id,
            description=args_descs.get(f"{arg.id:03d}", "No description available.")
        ) + "\n"
    return event_md_template.format(
        name=event.name,
        id=event.id,
        description=event_desc if event_desc else "No description available.",
        arguments=arguments_md if arguments_md else "| None | None | None |",
        return_type=event.return_type if event.return_type else "None",
        return_description=return_desc if return_desc else "No description available."
    )
    

def main():
    desc = load_event_descriptions()
    try:
        with open("../forge-server-manager.wiki/events.md", "w") as f:
            f.write("# Events\n\n")
            for event in Events.events.values():
                event_data = desc.get(f"{event.id:#06x}", {})
                f.write(generate_event_md(
                                        event, 
                                        event_data.get("description", ""), #type: ignore
                                        event_data.get("arguments", {}),   #type: ignore
                                        event_data.get("return", "")      #type: ignore
                                        ))
                f.write("\n---\n")
        return 0
    except Exception as e:
        print(f"Error writing to wiki file: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())