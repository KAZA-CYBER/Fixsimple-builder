def parse_inventory(lines):
    result = {}

    for line in lines:
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith('#'):
            continue

        parts = stripped_line.split(':', 1)
        if len(parts) != 2:
            raise ValueError("Invalid line format")

        name, quantity_str = parts
        name = ' '.join(name.split()).lower().strip()
        quantity = int(quantity_str.strip())

        if not name:
            raise ValueError("Item name cannot be empty")
        if quantity <= 0:
            raise ValueError("Quantity must be a positive integer")

        if name in result:
            result[name] += quantity
        else:
            result[name] = quantity

    return result