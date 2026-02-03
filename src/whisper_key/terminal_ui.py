import sys

def prompt_choice(message: str, options: list[str]) -> int:
    print()
    print(message)
    print()
    for i, option in enumerate(options, 1):
        print(f"  [{i}] {option}")
    print()

    valid_choices = [str(i) for i in range(1, len(options) + 1)]

    while True:
        try:
            choice = input(f"Choice [{'/'.join(valid_choices)}]: ").strip()
            if choice in valid_choices:
                return int(choice) - 1
            print(f"Please enter {' or '.join(valid_choices)}")
        except (KeyboardInterrupt, EOFError):
            return -1
