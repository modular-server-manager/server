from .bus import Events

def main():
    for id, event in Events.events.items():
        print(f"Event ID: {id}, Name: {event.name}")
        for arg in event.args:
            print(f"  Arg: {arg.name}, Type: {arg.type}")
