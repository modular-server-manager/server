import argparse
import os
import re
import sys

RE_INSTRUCTION = re.compile(r'{{(?P<instruction>.*)}}')



class Page:
    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return f"Page({self.name})"

class Template:
    def __init__(self, template_folder : str, template_name: str, page: Page|None = None):
        if page is None:
            page = Page(template_name)
        self.page = page
        self.template_folder = template_folder
        self.template_name = template_name

    def insert(self, template_name : str) -> str:
        """
        Include a template file.
        """
        return Template(self.template_folder, template_name, self.page).parse()


    def eval(self, instruction: str, page : Page) -> str:
        """
        Evaluate the instruction and return the result.
        """
        return eval(instruction, {"page": page, "insert": self.insert})


    def parse(self) -> str:
        file_path = f"{self.template_folder}/{self.template_name}.template.html"
        if not os.path.exists(file_path):
            file_path = f"{self.template_folder}/{self.template_name}.template"
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Template file {file_path} not found.")
        with open(file_path, 'r') as file:
            template = file.read()

        for match in RE_INSTRUCTION.finditer(template):
            instruction = match.group('instruction')
            try:
                result = self.eval(instruction, self.page)
            except Exception as e:
                raise RuntimeError(f"Error evaluating instruction '{instruction}' in template '{self.template_name}': {e}")
            else:
                template = template.replace(match.group(0), str(result))
        return template


def main():
    parser = argparse.ArgumentParser(description="Parse a template file.")
    parser.add_argument("template_folder", type=str, help="The folder containing the template files.")
    parser.add_argument("template_name", type=str, help="The name of the template file (without extension).")
    parser.add_argument("--output", '-o', type=str, help="Output file name (optional).", default=None)
    args = parser.parse_args()

    output = open(args.output, 'w') if args.output else sys.stdout

    template_folder = args.template_folder
    template_name = args.template_name

    template_parser = Template(template_folder, template_name)
    result = template_parser.parse()
    print(result, file=output)

if __name__ == "__main__":
    main()
