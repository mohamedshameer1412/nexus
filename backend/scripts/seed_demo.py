"""Seed a demo account with realistic study history, through the running API (so every rule applies) plus a few direct inserts.

    python -m uvicorn studyhub.web.app:app --port 8100        # in one terminal
    python scripts/seed_demo.py                              # in another  (NEXUS_API=http://127.0.0.1:8100)

Creates the user  demo@nexus.local / nexus-demo-2026  with:
  * "Data Structures & Algorithms": the sample course notes, practice questions with source quotes, a prerequisite graph,
    six quizzes spread over three weeks (improving), a study plan, self-ratings, flashcard reviews, notes, questions asked,
  * "Computer Networks": the sample Word notes and a first quiz,
  * a career goal from a short job description.
Practice questions are written here by hand (no model is needed); everything else goes through the same API the app uses.
Run it against a DEMO database only (STUDYHUB_DB): it rewrites timestamps of the demo user's quizzes to spread them over time.
"""
from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from studyhub.db import open_db  # noqa: E402

API = os.environ.get("NEXUS_API", "http://127.0.0.1:8100") + "/api/v1"
EMAIL, PASSWORD, USER = "demo@nexus.local", "nexus-demo-2026", "demo"
SAMPLES = ROOT / "data" / "sample-materials"
random.seed(7)

# topic -> [(question, [4 options], answer index, explanation, exact quote from the notes, difficulty)]
MCQ = {
    "Arrays": [
        ("How long does reading an array element by its index take?", ["O(1)", "O(log n)", "O(n)", "O(n log n)"], 0, "The address is computed directly from the index.", "so reading or writing any element by its index takes constant time, O(1)", "easy"),
        ("Why is inserting in the middle of an array O(n)?", ["The array must be sorted again", "Every later element must shift by one place", "The hash must be recomputed", "The array is copied twice"], 1, "Elements after the position move.", "Every element after the position must shift by one place, so these operations take linear time, O(n)", "medium"),
        ("What is the amortised cost of appending to a dynamic array?", ["O(n)", "O(log n)", "O(1)", "O(n squared)"], 2, "Doubling happens rarely.", "appending to a dynamic array costs O(1) amortised time", "medium"),
        ("How does a dynamic array usually grow?", ["By one slot at a time", "By linking a new block", "By allocating a larger block, usually double the size", "By compressing its elements"], 2, "It doubles and copies.", "A dynamic array such as a Python list grows by allocating a larger block, usually double the size", "hard"),
    ],
    "Linked Lists": [
        ("What does each node of a singly linked list hold?", ["Only a value", "A value and a reference to the next node", "An index and a hash", "Two child pointers"], 1, "Value plus next reference.", "each node holds a value and a reference to the next node", "easy"),
        ("How long does finding the element at position i take in a linked list?", ["O(1)", "O(log n)", "O(n)", "O(i squared)"], 2, "You walk from the head.", "Finding the element at position i, however, means walking from the head one node at a time, which takes linear time, O(n)", "medium"),
        ("What does a doubly linked list add?", ["A hash of each value", "A reference to the previous node", "A second head pointer", "Sorted order"], 1, "Each node also points backwards.", "A doubly linked list also stores a reference to the previous node", "medium"),
    ],
    "Stacks": [
        ("Which order does a stack follow?", ["First in, first out", "Last in, first out", "Sorted order", "Random order"], 1, "LIFO.", "A stack is a last-in first-out (LIFO) collection", "easy"),
        ("What does pop do?", ["Adds an element to the top", "Removes and returns the top element", "Returns the top without removing it", "Removes the bottom element"], 1, "Pop removes from the top.", "the pop operation removes and returns the element from the top", "easy"),
        ("What happens on a function call?", ["A frame is enqueued", "A frame holding locals and the return address is pushed", "The heap is sifted", "The stack is cleared"], 1, "Calls push frames.", "each call pushes a frame holding its local variables and return address", "medium"),
        ("Which task is a classic use of a stack?", ["Breadth-first search", "Checking whether brackets are balanced", "Hashing strings", "Scheduling printers"], 1, "Brackets are matched with a stack.", "checking whether brackets in an expression are balanced", "hard"),
    ],
    "Queues": [
        ("Which order does a queue follow?", ["Last in, first out", "First in, first out", "Priority order", "Sorted order"], 1, "FIFO.", "A queue is a first-in first-out (FIFO) collection", "easy"),
        ("Where does dequeue remove from?", ["The rear", "The front", "The middle", "The top"], 1, "Front.", "the dequeue operation removes the element at the front", "easy"),
        ("What lets a queue live in a fixed array?", ["A hash function", "A circular buffer with wrapping indices", "A binary heap", "Recursion"], 1, "Indices wrap around.", "A circular buffer implements a queue in a fixed array by letting the front and rear indices wrap around to the start", "medium"),
        ("Which search keeps discovered vertices in a queue?", ["Depth-first search", "Binary search", "Breadth-first search", "Dijkstra without a heap"], 2, "BFS uses a queue.", "for breadth-first search, where the vertices waiting to be visited are kept in the order they were discovered", "medium"),
    ],
    "Recursion": [
        ("What does every recursive function need?", ["A loop", "A base case answered without a further call", "A global variable", "A queue"], 1, "Otherwise it never stops.", "Every recursive function needs a base case that is answered directly without a further call", "easy"),
        ("What decides the memory used by recursion?", ["The number of variables", "The depth of recursion", "The size of the heap", "The input type"], 1, "Each call is a stack frame.", "the depth of recursion determines the memory used", "medium"),
        ("What makes naive recursive Fibonacci efficient?", ["Tail calls", "Memoisation", "Sorting", "Hashing the input"], 1, "Store computed results.", "can be made efficient with memoisation, which stores results that were already computed", "hard"),
        ("What is the base case of factorial?", ["factorial of 1 is 0", "factorial of 0 is 1", "factorial of n is n", "There is none"], 1, "0! = 1.", "with the factorial of 0 equal to 1 as the base case", "medium"),
    ],
    "Trees": [
        ("What is a leaf?", ["The root", "A node with no children", "A node with two children", "An edge"], 1, "No children.", "A node with no children is called a leaf", "easy"),
        ("What does inorder traversal visit first?", ["The node", "The right subtree", "The left subtree", "The root's parent"], 2, "Left, node, right.", "Inorder traversal visits the left subtree, then the node, then the right subtree", "medium"),
        ("Why are tree algorithms naturally recursive?", ["Trees are stored in arrays", "Every subtree is itself a tree", "Trees have cycles", "Leaves are sorted"], 1, "Self-similar structure.", "Tree algorithms are naturally recursive because every subtree is itself a tree", "medium"),
        ("How is the height of a tree defined?", ["Number of nodes", "Edges on the longest path from the root to a leaf", "Number of leaves", "Depth of the root"], 1, "Longest root-to-leaf path.", "the height of a tree is the number of edges on the longest path from the root to a leaf", "hard"),
    ],
    "Binary Search Trees": [
        ("Where are smaller keys kept in a binary search tree?", ["In the right subtree", "In the left subtree", "At the leaves only", "In a separate list"], 1, "Left is smaller.", "keeps every key in the left subtree smaller than the node's key", "easy"),
        ("What does an inorder traversal of a BST produce?", ["Keys in insertion order", "Keys in sorted order", "Keys in reverse order", "Only the leaves"], 1, "Sorted.", "an inorder traversal of a binary search tree visits the keys in sorted order", "medium"),
        ("What happens when keys are inserted in sorted order?", ["The tree stays balanced", "It degenerates into a linked-list shape", "It becomes a heap", "Insertion fails"], 1, "Degenerate tree.", "inserting keys in sorted order produces a degenerate tree that behaves like a linked list", "hard"),
        ("How do AVL and red-black trees keep the height logarithmic?", ["By rehashing", "By rotations after updates", "By sorting the keys", "By using a queue"], 1, "Rotations rebalance.", "perform rotations after updates to keep the height logarithmic", "hard"),
    ],
    "Heaps": [
        ("Where is the smallest element of a min-heap?", ["At a leaf", "At the root", "In the middle", "At the end of the array"], 1, "Heap property.", "so the smallest element is always at the root", "easy"),
        ("Where are the children of index i stored?", ["i+1 and i+2", "2i+1 and 2i+2", "i/2 and i/2+1", "2i and 3i"], 1, "Array layout.", "the children of the element at index i are at indices 2i plus 1 and 2i plus 2", "medium"),
        ("How long does removing the minimum take?", ["O(1)", "O(log n)", "O(n)", "O(n log n)"], 1, "Sift down.", "removing the minimum moves the last element to the root and sifts it down; both take O(log n) time", "medium"),
    ],
    "Hash Tables": [
        ("What is a collision?", ["Two keys hashing to the same index", "A full table", "A deleted key", "A negative hash"], 0, "Same index.", "Two different keys can hash to the same index, which is called a collision", "easy"),
        ("How does separate chaining handle collisions?", ["It probes for a free slot", "It stores colliding entries in a list at that index", "It rejects the key", "It resizes immediately"], 1, "Lists per bucket.", "Separate chaining stores all colliding entries in a list at that index", "medium"),
        ("What happens when the load factor grows too high?", ["Lookups become O(1)", "The table is resized and keys are rehashed", "Keys are sorted", "The hash function changes randomly"], 1, "Resize and rehash.", "the table is resized and every key is rehashed into the larger array", "medium"),
    ],
    "Graphs": [
        ("Which search finds shortest paths in an unweighted graph?", ["Depth-first search", "Breadth-first search", "Binary search", "Heapsort"], 1, "BFS explores level by level.", "Breadth-first search explores a graph level by level using a queue and finds the shortest path in an unweighted graph", "medium"),
        ("How much memory does an adjacency list use?", ["Proportional to vertices squared", "Proportional to vertices plus edges", "Constant", "Proportional to edges squared"], 1, "V + E.", "uses memory proportional to the number of vertices plus edges", "medium"),
        ("What does Dijkstra's algorithm require of edge weights?", ["They are negative", "They are non-negative", "They are equal", "They are integers"], 1, "Non-negative.", "Dijkstra's algorithm finds shortest paths in a graph with non-negative edge weights", "hard"),
        ("How is depth-first search usually implemented?", ["With a queue", "With recursion or an explicit stack", "With a hash table", "With sorting"], 1, "Stack-based.", "is usually implemented with recursion or an explicit stack", "hard"),
    ],
    "Sorting": [
        ("What is merge sort's running time?", ["O(n squared) always", "O(n log n) always", "O(n) always", "O(log n)"], 1, "Always n log n.", "it always takes O(n log n) time and is stable", "easy"),
        ("When is quicksort O(n squared)?", ["Never", "When the pivots are chosen badly", "When the array is small", "When keys are equal"], 1, "Bad pivots.", "O(n squared) in the worst case when the pivots are chosen badly", "medium"),
        ("What makes a sort stable?", ["It uses no extra memory", "Equal keys keep their original relative order", "It runs in O(n log n)", "It is recursive"], 1, "Order of equal keys.", "A sorting algorithm is stable when elements with equal keys keep their original relative order", "medium"),
        ("Which sort suits small or nearly sorted inputs?", ["Merge sort", "Insertion sort", "Heapsort", "Quicksort"], 1, "Insertion sort.", "Insertion sort builds the sorted array one element at a time and is efficient for small or nearly sorted inputs", "hard"),
    ],
}
PREREQS = [("Linked Lists", "Arrays"), ("Recursion", "Stacks"), ("Trees", "Recursion"), ("Binary Search Trees", "Trees"), ("Heaps", "Trees"),
           ("Hash Tables", "Arrays"), ("Graphs", "Queues"), ("Sorting", "Recursion")]
# how likely the demo student answers each topic correctly, per quiz (improving over time, one topic slipping)
SKILL = {"Arrays": .9, "Linked Lists": .8, "Stacks": .85, "Queues": .75, "Recursion": .35, "Trees": .45, "Binary Search Trees": .4, "Heaps": .55,
         "Hash Tables": .7, "Graphs": .5, "Sorting": .6}


class Client:
    def __init__(self):
        self.c = httpx.Client(timeout=120)
        self.csrf = self.c.get(f"{API}/session").json()["csrf"]

    def req(self, method, path, **kw):
        r = self.c.request(method, API + path, headers={"X-CSRF-Token": self.csrf}, **kw)
        if r.headers.get("content-type", "").startswith("application/json"):
            j = r.json()
            if isinstance(j, dict) and "csrf" in j:
                self.csrf = j["csrf"]
        return r


def main():
    a = Client()
    r = a.req("POST", "/register", json={"username": USER, "email": EMAIL, "password": PASSWORD})
    if r.status_code != 201:
        r = a.req("POST", "/login", json={"email": EMAIL, "password": PASSWORD})
        if r.status_code != 200:
            sys.exit(f"could not register or sign in: {r.status_code} {r.text}")
        print("demo user exists; signing in and adding to it")
    subjects = {s["name"]: s["id"] for s in a.req("GET", "/subjects").json()["subjects"]}
    if "Data Structures & Algorithms" in subjects:
        sys.exit("already seeded (subject exists). Use a fresh STUDYHUB_DB to seed again.")

    dsa = a.req("POST", "/subjects", json={"name": "Data Structures & Algorithms", "description": "CS201, semester 3. Core structures, recursion, trees, graphs and sorting."}).json()["id"]
    net = a.req("POST", "/subjects", json={"name": "Computer Networks", "description": "CS305. Layers, protocols and routing."}).json()["id"]
    a.req("PUT", f"/subjects/{dsa}/level", json={"level": "intermediate"})
    a.req("PUT", f"/subjects/{net}/level", json={"level": "new"})
    for sid, name, role in [(dsa, "dsa-course-notes.txt", "notes"), (net, "networks.docx", "notes")]:
        p = SAMPLES / name
        if p.exists():
            r = a.req("POST", f"/subjects/{sid}/materials", files={"file": (name, p.read_bytes())}, data={"role": role})
            print("upload", name, r.status_code)

    store = open_db()
    db = store.db
    uid = db.execute("SELECT id FROM users WHERE username=?", (USER,)).fetchone()[0]
    topics = {r["name"]: r["id"] for r in db.execute("SELECT id, name FROM topics WHERE subject_id=?", (dsa,))}
    paths = {r["name"]: r["path"] for r in db.execute("SELECT name, path FROM topics WHERE subject_id=?", (dsa,))}
    now = time.time()
    n = 0
    for topic, qs in MCQ.items():
        if topic not in topics:
            print("missing topic", topic)
            continue
        for i, (q, opts, ans, why, quote, diff) in enumerate(qs):
            chunk = db.execute("SELECT c.id, d.title, c.page_start, c.page_end, c.heading_path FROM chunks c JOIN documents d ON d.id=c.document_id "
                               "WHERE c.subject_id=? AND c.topic_id=? AND instr(c.text, ?) > 0 LIMIT 1", (dsa, topics[topic], quote[:60])).fetchone()
            db.execute("INSERT INTO mcq_items(subject_id, topic_id, topic_path, question, options, answer_index, explanation, quote, chunk_id, doc_title, page_start, page_end, "
                       "heading_path, solver, model, key, created_at, difficulty) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (dsa, topics[topic], paths[topic], q, json.dumps(opts), ans, why, quote, chunk["id"] if chunk else None, chunk["title"] if chunk else "Course notes",
                        chunk["page_start"] if chunk else None, chunk["page_end"] if chunk else None, chunk["heading_path"] if chunk else topic, "agreed", "seeded by hand",
                        f"demo-{topics[topic]}-{i}", now - 22 * 86400, diff))
            n += 1
    ntopics = {r["name"]: r["id"] for r in db.execute("SELECT id, name FROM topics WHERE subject_id=?", (net,))}
    net_first = next(iter(ntopics.items()), None)
    if net_first:
        for i, (q, opts, ans) in enumerate([("How many layers does the OSI model have?", ["4", "5", "7", "9"], 2),
                                            ("Which layer routes packets between networks?", ["Physical", "Network", "Session", "Application"], 1),
                                            ("Which protocol gives reliable, ordered delivery?", ["UDP", "IP", "TCP", "ARP"], 2)]):
            db.execute("INSERT INTO mcq_items(subject_id, topic_id, topic_path, question, options, answer_index, explanation, quote, key, created_at, difficulty) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                       (net, net_first[1], net_first[0], q, json.dumps(opts), ans, "From the course notes.", "See the notes.", f"demo-net-{i}", now - 5 * 86400, "easy"))
    for t, p in PREREQS:
        if t in topics and p in topics:
            db.execute("INSERT OR REPLACE INTO topic_prereqs(topic_id, prereq_id, confirmed, origin) VALUES (?,?,1,'manual')", (topics[t], topics[p]))
    print("practice questions", n)
    by_item = {r["id"]: r for r in db.execute("SELECT m.id, m.answer_index, t.name FROM mcq_items m JOIN topics t ON t.id=m.topic_id WHERE m.subject_id IN (?,?)", (dsa, net))}

    def take(sid, kind, mode, days_ago, lift):
        r = a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"kind": kind, "mode": mode})
        aid = r.json()["id"]
        answered = 0
        while True:
            st = a.req("GET", f"/subjects/{sid}/quiz/attempts/{aid}").json()
            if st["state"] != "mcq":
                break
            it = st["item"]
            m = by_item[it["item_id"]]
            p = min(0.97, SKILL.get(m["name"], .6) + lift)
            chosen = m["answer_index"] if random.random() < p else (m["answer_index"] + random.randint(1, 3)) % 4
            a.req("POST", f"/subjects/{sid}/quiz/attempts/{aid}/answer", json={"answer_row_id": it["answer_row_id"], "item_id": it["item_id"], "chosen": chosen,
                                                                            "response_time": round(random.uniform(6, 38) * (1.3 if p < .5 else 1), 1), "hesitations": random.randint(0, 2)})
            answered += 1
            if answered > 40:
                break
        if mode == "assessment" and random.random() < 0.6:
            a.req("POST", f"/subjects/{sid}/quiz/attempts/{aid}/events", json={"event_type": "tab_switch"})
        a.req("POST", f"/subjects/{sid}/quiz/attempts/{aid}/finish")
        # spread the history over time: shift this attempt back
        shift = days_ago * 86400 + random.randint(3600 * 8, 3600 * 13)
        db.execute("UPDATE quiz_attempts SET started_at=started_at-?, finished_at=finished_at-? WHERE id=?", (shift, shift, aid))
        db.execute("UPDATE attempt_answers SET answered_at=answered_at-? WHERE attempt_id=?", (shift, aid))
        db.execute("UPDATE quiz_proctoring_events SET captured_at=captured_at-? WHERE attempt_id=?", (shift, aid))
        print(f"quiz {aid} ({kind}, {mode}) {days_ago} days ago: {answered} answers")
        return aid

    plan = [("diagnostic", "practice", 20, -0.05), ("standard", "practice", 16, 0.0), ("standard", "practice", 12, 0.05), ("revision", "practice", 9, 0.08),
            ("standard", "assessment", 5, 0.12), ("standard", "practice", 2, 0.15), ("standard", "assessment", 0, 0.18)]
    last = None
    for kind, mode, days, lift in plan:
        try:
            last = take(dsa, kind, mode, days, lift)
        except Exception as e:  # a revision quiz can have nothing to revise
            print("skipped", kind, e)
    take(net, "diagnostic", "practice", 3, 0.0)

    # study plan, exam date, self-ratings, flashcards, notes, questions, career goal
    exam = time.strftime("%Y-%m-%d", time.gmtime(now + 38 * 86400))
    a.req("PUT", f"/subjects/{dsa}/roadmap/profile", json={"goal": "Score 80%+ in the end-semester exam", "hours_per_week": 6, "exam_date": exam})
    ratings = {topics[k]: v for k, v in {"Arrays": 5, "Stacks": 4, "Recursion": 4, "Trees": 3, "Binary Search Trees": 4, "Graphs": 2, "Sorting": 3}.items() if k in topics}
    a.req("PUT", f"/subjects/{dsa}/self-check", json={"ratings": {str(k): v for k, v in ratings.items()}})
    cards = a.req("GET", f"/subjects/{dsa}/flashcards").json().get("cards", [])[:12]
    for c in cards:
        a.req("POST", f"/subjects/{dsa}/flashcards/{c['item_id']}/review", json={"grade": random.choice(["good", "good", "easy", "again", "hard"])})
    a.req("POST", f"/subjects/{dsa}/notes", json={"title": "Big-O cheat sheet", "body": "## Access and search\n\n- Array index: **O(1)**\n- Linked list index: **O(n)**\n- BST search: **O(log n)** when balanced\n- Hash table lookup: **O(1)** on average\n\n## Sorting\n\n- Merge sort: O(n log n), stable, O(n) memory\n- Quicksort: O(n log n) average, O(n²) worst\n"})
    a.req("POST", f"/subjects/{dsa}/notes", json={"title": "Recursion checklist", "body": "1. Write the base case first\n2. Make every call smaller\n3. Watch the call-stack depth\n4. Memoise repeated subproblems\n"})
    for q in ["What does pop do on a stack?", "Why is an inorder traversal of a binary search tree sorted?", "How does a hash table handle collisions?"]:
        a.req("POST", f"/subjects/{dsa}/questions", json={"question": q})
    jd = ("Graduate Software Engineer. Required: strong data structures and algorithms, recursion, trees and graphs, hash tables, sorting. "
          "You will design efficient back-end services, analyse time complexity with Big-O, and write clean code. Nice to have: computer networks, TCP/IP.")
    a.req("POST", "/career", json={"title": "Graduate Software Engineer", "text": jd})
    a.req("POST", f"/subjects/{dsa}/notes/smart", json={})
    a.req("GET", f"/subjects/{dsa}/agents")
    store.close()
    print(f"\nDone. Sign in as {EMAIL} / {PASSWORD}")


if __name__ == "__main__":
    main()
