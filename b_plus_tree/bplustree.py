import json
import os
import struct


class BPlusTreeNode:
    def __init__(self, is_leaf=False, block_factor=3):
        self.is_leaf = is_leaf
        self.block_factor = block_factor
        self.keys = []
        self.children = []
        self.next_leaf = -1  # ✅ CORREGIDO: -1 en lugar de None
        self.size = 0

    def is_full(self):
        return self.size > self.block_factor

    def to_dict(self):
        return {
            'is_leaf': self.is_leaf,
            'block_factor': self.block_factor,
            'keys': self.keys,
            'children': self.children,
            'next_leaf': self.next_leaf if self.next_leaf is not None else -1,
            'size': self.size
        }

    @staticmethod
    def from_dict(data):
        node = BPlusTreeNode(is_leaf=data["is_leaf"],
                             block_factor=data.get("block_factor", 3))
        node.keys = data["keys"]
        node.children = data["children"]
        node.next_leaf = data.get("next_leaf", -1)
        if node.next_leaf is None:
            node.next_leaf = -1
        node.size = data.get("size", len(data["keys"]))
        return node


class BPlusFile:
    HEADER_SIZE = 4

    def __init__(self, storage_path="bplustree_nodes", index_name="default"):
        self.storage_path = storage_path
        self.index_name = index_name
        self.filename = os.path.join(storage_path, f"{index_name}_index.dat")
        os.makedirs(storage_path, exist_ok=True)

        if not os.path.exists(self.filename):
            self.initialize_file()

    def initialize_file(self):
        with open(self.filename, "wb") as file:
            header = -1
            file.write(struct.pack("i", header))

    def get_header(self):
        with open(self.filename, "rb") as file:
            file.seek(0)
            data = file.read(self.HEADER_SIZE)
            if not data:
                return -1
            root_position = struct.unpack("i", data)[0]
            return root_position

    def write_header(self, root_position):
        with open(self.filename, "rb+") as file:
            file.seek(0)
            file.write(struct.pack("i", root_position))

    def read_node(self, node_id):
        if node_id == -1:
            raise ValueError(f"Invalid node_id: {node_id}")
        if node_id is None:
            raise ValueError(f"node_id cannot be None")

        path = os.path.join(self.storage_path, f"node_{node_id}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Node file not found: {path}")

        with open(path, "r") as f:
            data = json.load(f)
            return BPlusTreeNode.from_dict(data)

    def write_node(self, node, node_id=None):
        if node_id is None:
            node_id = self._get_next_node_id()
        path = os.path.join(self.storage_path, f"node_{node_id}.json")
        with open(path, "w") as f:
            json.dump(node.to_dict(), f)
        return node_id

    def _get_next_node_id(self):
        existing_files = [f for f in os.listdir(self.storage_path)
                          if f.startswith("node_") and f.endswith(".json")]
        if not existing_files:
            return 0
        ids = [int(f.split("_")[1].split(".")[0]) for f in existing_files]
        return max(ids) + 1


class BPlusTree:
    def __init__(self, order=None, storage_path="bplustree_nodes", index_name="default"):
        self.order = order if order is not None else 3
        self.storage_path = storage_path
        self.index_name = index_name
        self.index_file = BPlusFile(storage_path, index_name)
        self.root_id = self.index_file.get_header()

        if self.root_id == -1:
            root = BPlusTreeNode(is_leaf=True, block_factor=self.order)
            self.root_id = self.index_file.write_node(root, 0)
            self.index_file.write_header(self.root_id)

    def search(self, key):
        if self.root_id == -1:
            return None
        return self._search_aux(self.root_id, key)

    def _search_aux(self, node_id, key):
        node = self.index_file.read_node(node_id)

        if node.is_leaf:
            for k, ref in node.keys:
                if k == key:
                    return ref
            return None

        i = 0
        while i < node.size and node.keys[i] < key:
            i += 1
        return self._search_aux(node.children[i], key)

    def range_search(self, start, end):
        if self.root_id == -1:
            return []

        leaf_id = self._find_leaf_id(self.root_id, start)
        results = []

        current_id = leaf_id
        while current_id != -1 and current_id is not None:
            current_node = self.index_file.read_node(current_id)
            for k, ref in current_node.keys:
                if start <= k <= end:
                    results.append((k, ref))
                elif k > end:
                    return results
            current_id = current_node.next_leaf

            if current_id is None:
                break

        return results

    def add(self, key, record_ref=None):
        split, new_key, new_pointer = self._insert_aux(self.root_id, key, record_ref)

        if split:
            new_root = BPlusTreeNode(is_leaf=False, block_factor=self.order)
            new_root.keys = [new_key]
            new_root.children = [self.root_id, new_pointer]
            new_root.size = 1

            self.root_id = self.index_file.write_node(new_root)
            self.index_file.write_header(self.root_id)

    def _insert_aux(self, node_id, key, pointer):
        node = self.index_file.read_node(node_id)

        if node.is_leaf:
            node.keys.append((key, pointer))
            node.keys.sort(key=lambda x: x[0])
            node.size = len(node.keys)

            if not node.is_full():
                self.index_file.write_node(node, node_id)
                return False, None, -1

            mid = node.size // 2
            left_keys = node.keys[:mid]
            right_keys = node.keys[mid:]

            new_node = BPlusTreeNode(is_leaf=True, block_factor=self.order)
            new_node.keys = right_keys
            new_node.size = len(right_keys)
            new_node.next_leaf = node.next_leaf if node.next_leaf is not None else -1

            new_node_id = self.index_file.write_node(new_node)

            node.keys = left_keys
            node.size = len(left_keys)
            node.next_leaf = new_node_id
            self.index_file.write_node(node, node_id)

            return True, new_node.keys[0][0], new_node_id

        else:
            i = 0
            while i < node.size and node.keys[i] < key:
                i += 1

            split, new_key, new_pointer = self._insert_aux(node.children[i], key, pointer)

            if not split:
                return False, None, -1

            node.keys.insert(i, new_key)
            node.children.insert(i + 1, new_pointer)
            node.size += 1

            if not node.is_full():
                self.index_file.write_node(node, node_id)
                return False, None, -1

            mid = node.size // 2
            up_key = node.keys[mid]
            left_keys = node.keys[:mid]
            right_keys = node.keys[mid + 1:]
            left_children = node.children[:mid + 1]
            right_children = node.children[mid + 1:]

            new_node = BPlusTreeNode(is_leaf=False, block_factor=self.order)
            new_node.keys = right_keys
            new_node.children = right_children
            new_node.size = len(right_keys)

            new_node_id = self.index_file.write_node(new_node)
            node.keys = left_keys
            node.children = left_children
            node.size = len(left_keys)
            self.index_file.write_node(node, node_id)

            return True, up_key, new_node_id

    def remove(self, key):
        """Versión simple: elimina sin rebalanceo completo"""
        self._delete_aux(self.root_id, key)

        root = self.index_file.read_node(self.root_id)
        if not root.is_leaf and root.size == 0:
            if root.children:
                self.root_id = root.children[0]
                self.index_file.write_header(self.root_id)

    def _delete_aux(self, node_id, key):
        node = self.index_file.read_node(node_id)

        if node.is_leaf:
            node.keys = [(k, ref) for k, ref in node.keys if k != key]
            node.size = len(node.keys)
            self.index_file.write_node(node, node_id)
        else:
            i = 0
            while i < node.size and node.keys[i] < key:
                i += 1
            self._delete_aux(node.children[i], key)

    def delete(self, key):
        self.remove(key)

    def get_all(self):
        if self.root_id == -1:
            return []

        leaf_id = self._find_first_leaf(self.root_id)
        results = []

        current_id = leaf_id
        while current_id != -1 and current_id is not None:
            current_node = self.index_file.read_node(current_id)
            for k, ref in current_node.keys:
                results.append((k, ref))
            current_id = current_node.next_leaf

            if current_id is None:
                break

        return results

    def _find_first_leaf(self, node_id):
        node = self.index_file.read_node(node_id)

        while not node.is_leaf:
            node_id = node.children[0]
            node = self.index_file.read_node(node_id)

        return node_id

    def _find_leaf_id(self, node_id, key):
        node = self.index_file.read_node(node_id)

        if node.is_leaf:
            return node_id

        i = 0
        while i < node.size and node.keys[i] < key:
            i += 1
        return self._find_leaf_id(node.children[i], key)

    def clear(self):
        if os.path.exists(self.storage_path):
            for file in os.listdir(self.storage_path):
                file_path = os.path.join(self.storage_path, file)
                os.remove(file_path)
        self.index_file.initialize_file()
        root = BPlusTreeNode(is_leaf=True, block_factor=self.order)
        self.root_id = self.index_file.write_node(root, 0)
        self.index_file.write_header(self.root_id)

    def print_tree(self):
        if self.root_id == -1:
            print("Tree is empty.")
            return

        queue = [(self.root_id, 0)]
        current_level = 0

        print(f"Level {current_level}: ", end="")
        while queue:
            node_id, level = queue.pop(0)
            node = self.index_file.read_node(node_id)

            if level != current_level:
                current_level = level
                print()
                print(f"Level {current_level}: ", end="")

            if node.is_leaf:
                keys = [k for k, _ in node.keys]
            else:
                keys = node.keys
            print(f" {keys}", end="  ")

            if not node.is_leaf:
                for child_id in node.children[:node.size + 1]:
                    if child_id != -1:
                        queue.append((child_id, level + 1))
        print()


if __name__ == "__main__":
    print("=" * 60)
    print("PRUEBAS DEL B+ TREE")
    print("=" * 60)

    tree = BPlusTree(order=4, index_name="test")
    tree.clear()

    print("\n1. INSERCIÓN")
    print("-" * 60)
    keys = [10, 20, 5, 6, 12, 30, 7, 17, 3, 15, 25, 8]
    for key in keys:
        tree.add(key, f"record_{key}")
        print(f"✓ Insertado: {key}")

    print("\n2. ESTRUCTURA DEL ÁRBOL")
    print("-" * 60)
    tree.print_tree()

    print("\n3. BÚSQUEDA")
    print("-" * 60)
    for key in [10, 5, 30, 100]:
        result = tree.search(key)
        print(f"Buscar {key}: {result if result else 'NO encontrado'}")

    print("\n4. BÚSQUEDA POR RANGO")
    print("-" * 60)
    results = tree.range_search(5, 15)
    print(f"Rango [5, 15]: {len(results)} registros")
    print(f"  {results}")

    print("\n5. OBTENER TODOS")
    print("-" * 60)
    all_records = tree.get_all()
    print(f"Total: {len(all_records)} registros")

    print("\n6. ELIMINACIÓN")
    print("-" * 60)
    tree.remove(10)
    print(f"Eliminado: 10")
    print(f"Buscar 10: {tree.search(10)}")

    print("\n7. VALIDACIÓN DE ORDEN")
    print("-" * 60)
    all_keys = [k for k, _ in tree.get_all()]
    is_sorted = all_keys == sorted(all_keys)
    print(f"Claves en orden: {'✓ SÍ' if is_sorted else '✗ NO'}")
    if not is_sorted:
        print(f"  Actual: {all_keys}")
        print(f"  Esperado: {sorted(all_keys)}")

    print("\n" + "=" * 60)
    print("PRUEBAS COMPLETADAS")
    print("=" * 60)