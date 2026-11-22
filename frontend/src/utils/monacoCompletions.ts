/**
 * Monaco Editor IntelliSense & Autocompletion Provider
 * Provides rich VS Code-style method suggestions on '.' (dot) and word triggers
 * for Python, Java, C, and C++.
 */

let isRegistered = false

interface CompletionDef {
  label: string
  detail: string
  documentation: string
  insertText: string
  kind?: 'Method' | 'Function' | 'Property' | 'Class' | 'Keyword' | 'Snippet'
}

const PYTHON_COMPLETIONS: CompletionDef[] = [
  // List methods
  { label: 'append', detail: 'list.append(x)', documentation: 'Append object to the end of the list.', insertText: 'append(${1:item})', kind: 'Method' },
  { label: 'extend', detail: 'list.extend(iterable)', documentation: 'Extend list by appending elements from the iterable.', insertText: 'extend(${1:iterable})', kind: 'Method' },
  { label: 'insert', detail: 'list.insert(index, x)', documentation: 'Insert an item at a given position.', insertText: 'insert(${1:index}, ${2:item})', kind: 'Method' },
  { label: 'remove', detail: 'list.remove(x)', documentation: 'Remove first occurrence of value.', insertText: 'remove(${1:item})', kind: 'Method' },
  { label: 'pop', detail: 'list.pop([index])', documentation: 'Remove and return item at index (default last).', insertText: 'pop(${1:index})', kind: 'Method' },
  { label: 'clear', detail: 'list.clear()', documentation: 'Remove all items from list.', insertText: 'clear()', kind: 'Method' },
  { label: 'index', detail: 'list.index(x[, start[, end]])', documentation: 'Return zero-based index of first occurrence.', insertText: 'index(${1:item})', kind: 'Method' },
  { label: 'count', detail: 'list.count(x)', documentation: 'Return number of occurrences of value.', insertText: 'count(${1:item})', kind: 'Method' },
  { label: 'sort', detail: 'list.sort(key=None, reverse=False)', documentation: 'Sort the list in ascending order in place.', insertText: 'sort()', kind: 'Method' },
  { label: 'reverse', detail: 'list.reverse()', documentation: 'Reverse the elements of the list in place.', insertText: 'reverse()', kind: 'Method' },
  { label: 'copy', detail: 'list.copy()', documentation: 'Return a shallow copy of the list.', insertText: 'copy()', kind: 'Method' },

  // String methods
  { label: 'split', detail: 'str.split(sep=None, maxsplit=-1)', documentation: 'Return a list of words in the string.', insertText: 'split(${1:sep})', kind: 'Method' },
  { label: 'join', detail: 'str.join(iterable)', documentation: 'Concatenate strings in the iterable with separator.', insertText: 'join(${1:iterable})', kind: 'Method' },
  { label: 'strip', detail: 'str.strip([chars])', documentation: 'Return a copy of string with leading/trailing whitespace removed.', insertText: 'strip()', kind: 'Method' },
  { label: 'lstrip', detail: 'str.lstrip([chars])', documentation: 'Strip leading whitespace.', insertText: 'lstrip()', kind: 'Method' },
  { label: 'rstrip', detail: 'str.rstrip([chars])', documentation: 'Strip trailing whitespace.', insertText: 'rstrip()', kind: 'Method' },
  { label: 'replace', detail: 'str.replace(old, new[, count])', documentation: 'Return a copy with occurrences of substring replaced.', insertText: 'replace(${1:old}, ${2:new})', kind: 'Method' },
  { label: 'lower', detail: 'str.lower()', documentation: 'Return a copy of string converted to lowercase.', insertText: 'lower()', kind: 'Method' },
  { label: 'upper', detail: 'str.upper()', documentation: 'Return a copy of string converted to uppercase.', insertText: 'upper()', kind: 'Method' },
  { label: 'startswith', detail: 'str.startswith(prefix)', documentation: 'Test if string starts with the given prefix.', insertText: 'startswith(${1:prefix})', kind: 'Method' },
  { label: 'endswith', detail: 'str.endswith(suffix)', documentation: 'Test if string ends with the given suffix.', insertText: 'endswith(${1:suffix})', kind: 'Method' },
  { label: 'find', detail: 'str.find(sub)', documentation: 'Return lowest index where substring sub is found.', insertText: 'find(${1:sub})', kind: 'Method' },
  { label: 'isdigit', detail: 'str.isdigit()', documentation: 'Check if all characters in the string are digits.', insertText: 'isdigit()', kind: 'Method' },
  { label: 'isalpha', detail: 'str.isalpha()', documentation: 'Check if all characters in the string are alphabetic.', insertText: 'isalpha()', kind: 'Method' },
  { label: 'format', detail: 'str.format(*args, **kwargs)', documentation: 'Perform string formatting.', insertText: 'format(${1:args})', kind: 'Method' },

  // Dict methods
  { label: 'keys', detail: 'dict.keys()', documentation: 'Return a set-like view of dict keys.', insertText: 'keys()', kind: 'Method' },
  { label: 'values', detail: 'dict.values()', documentation: 'Return a view of dict values.', insertText: 'values()', kind: 'Method' },
  { label: 'items', detail: 'dict.items()', documentation: 'Return a set-like view of (key, value) pairs.', insertText: 'items()', kind: 'Method' },
  { label: 'get', detail: 'dict.get(key, default=None)', documentation: 'Return value for key if key is in dictionary.', insertText: 'get(${1:key}, ${2:default})', kind: 'Method' },
  { label: 'setdefault', detail: 'dict.setdefault(key, default=None)', documentation: 'Insert key with default value if not present.', insertText: 'setdefault(${1:key}, ${2:default})', kind: 'Method' },
  { label: 'update', detail: 'dict.update(other)', documentation: 'Update dict with key/value pairs from other.', insertText: 'update(${1:other})', kind: 'Method' },

  // Set methods
  { label: 'add', detail: 'set.add(elem)', documentation: 'Add an element to the set.', insertText: 'add(${1:elem})', kind: 'Method' },
  { label: 'discard', detail: 'set.discard(elem)', documentation: 'Remove an element from set if present.', insertText: 'discard(${1:elem})', kind: 'Method' },
  { label: 'union', detail: 'set.union(*s)', documentation: 'Return union of sets as a new set.', insertText: 'union(${1:other})', kind: 'Method' },
  { label: 'intersection', detail: 'set.intersection(*s)', documentation: 'Return intersection of sets.', insertText: 'intersection(${1:other})', kind: 'Method' },

  // Standard modules & math
  { label: 'math.sqrt', detail: 'math.sqrt(x)', documentation: 'Return square root of x.', insertText: 'math.sqrt(${1:x})', kind: 'Function' },
  { label: 'math.floor', detail: 'math.floor(x)', documentation: 'Return largest integer <= x.', insertText: 'math.floor(${1:x})', kind: 'Function' },
  { label: 'math.ceil', detail: 'math.ceil(x)', documentation: 'Return smallest integer >= x.', insertText: 'math.ceil(${1:x})', kind: 'Function' },
  { label: 'math.gcd', detail: 'math.gcd(a, b)', documentation: 'Return greatest common divisor of a and b.', insertText: 'math.gcd(${1:a}, ${2:b})', kind: 'Function' },
  { label: 'math.inf', detail: 'math.inf', documentation: 'Positive floating-point infinity.', insertText: 'math.inf', kind: 'Property' },
  { label: 'collections.deque', detail: 'deque([iterable[, maxlen]])', documentation: 'Double-ended queue with O(1) appends and pops on either side.', insertText: 'collections.deque(${1:iterable})', kind: 'Class' },
  { label: 'collections.Counter', detail: 'Counter([iterable-or-mapping])', documentation: 'Dict subclass for counting hashable items.', insertText: 'collections.Counter(${1:iterable})', kind: 'Class' },
  { label: 'collections.defaultdict', detail: 'defaultdict(default_factory)', documentation: 'Dict subclass that calls a factory function to supply missing values.', insertText: 'collections.defaultdict(${1:list})', kind: 'Class' },
  { label: 'heapq.heappush', detail: 'heapq.heappush(heap, item)', documentation: 'Push item onto heap, maintaining heap invariant.', insertText: 'heapq.heappush(${1:heap}, ${2:item})', kind: 'Function' },
  { label: 'heapq.heappop', detail: 'heapq.heappop(heap)', documentation: 'Pop and return smallest item from heap.', insertText: 'heapq.heappop(${1:heap})', kind: 'Function' },
  { label: 'bisect.bisect_left', detail: 'bisect_left(a, x)', documentation: 'Locate insertion point for x in a to maintain sorted order.', insertText: 'bisect.bisect_left(${1:a}, ${2:x})', kind: 'Function' },
]

const JAVA_COMPLETIONS: CompletionDef[] = [
  // String methods
  { label: 'length', detail: 'public int length()', documentation: 'Returns length of this string.', insertText: 'length()', kind: 'Method' },
  { label: 'charAt', detail: 'public char charAt(int index)', documentation: 'Returns char value at specified index.', insertText: 'charAt(${1:index})', kind: 'Method' },
  { label: 'substring', detail: 'public String substring(int beginIndex, int endIndex)', documentation: 'Returns a substring of this string.', insertText: 'substring(${1:beginIndex}, ${2:endIndex})', kind: 'Method' },
  { label: 'indexOf', detail: 'public int indexOf(String str)', documentation: 'Returns index within this string of first occurrence.', insertText: 'indexOf(${1:str})', kind: 'Method' },
  { label: 'equals', detail: 'public boolean equals(Object anObject)', documentation: 'Compares this string to specified object.', insertText: 'equals(${1:other})', kind: 'Method' },
  { label: 'equalsIgnoreCase', detail: 'public boolean equalsIgnoreCase(String anotherString)', documentation: 'Compares ignoring case.', insertText: 'equalsIgnoreCase(${1:another})', kind: 'Method' },
  { label: 'contains', detail: 'public boolean contains(CharSequence s)', documentation: 'Returns true if string contains char sequence.', insertText: 'contains(${1:sequence})', kind: 'Method' },
  { label: 'startsWith', detail: 'public boolean startsWith(String prefix)', documentation: 'Tests if this string starts with prefix.', insertText: 'startsWith(${1:prefix})', kind: 'Method' },
  { label: 'endsWith', detail: 'public boolean endsWith(String suffix)', documentation: 'Tests if this string ends with suffix.', insertText: 'endsWith(${1:suffix})', kind: 'Method' },
  { label: 'toLowerCase', detail: 'public String toLowerCase()', documentation: 'Converts all characters to lowercase.', insertText: 'toLowerCase()', kind: 'Method' },
  { label: 'toUpperCase', detail: 'public String toUpperCase()', documentation: 'Converts all characters to uppercase.', insertText: 'toUpperCase()', kind: 'Method' },
  { label: 'trim', detail: 'public String trim()', documentation: 'Returns string with leading/trailing whitespace removed.', insertText: 'trim()', kind: 'Method' },
  { label: 'split', detail: 'public String[] split(String regex)', documentation: 'Splits this string around matches of given regex.', insertText: 'split(${1:regex})', kind: 'Method' },
  { label: 'toCharArray', detail: 'public char[] toCharArray()', documentation: 'Converts this string to a new character array.', insertText: 'toCharArray()', kind: 'Method' },
  { label: 'replace', detail: 'public String replace(CharSequence target, CharSequence replacement)', documentation: 'Replaces each substring matching target.', insertText: 'replace(${1:target}, ${2:replacement})', kind: 'Method' },
  { label: 'isEmpty', detail: 'public boolean isEmpty()', documentation: 'Returns true if length is 0.', insertText: 'isEmpty()', kind: 'Method' },

  // List & Collections
  { label: 'add', detail: 'public boolean add(E e)', documentation: 'Appends specified element to collection.', insertText: 'add(${1:e})', kind: 'Method' },
  { label: 'get', detail: 'public E get(int index)', documentation: 'Returns element at specified index.', insertText: 'get(${1:index})', kind: 'Method' },
  { label: 'set', detail: 'public E set(int index, E element)', documentation: 'Replaces element at specified position.', insertText: 'set(${1:index}, ${2:element})', kind: 'Method' },
  { label: 'remove', detail: 'public E remove(int index)', documentation: 'Removes element at specified index.', insertText: 'remove(${1:index})', kind: 'Method' },
  { label: 'size', detail: 'public int size()', documentation: 'Returns number of elements in collection.', insertText: 'size()', kind: 'Method' },
  { label: 'clear', detail: 'public void clear()', documentation: 'Removes all elements from collection.', insertText: 'clear()', kind: 'Method' },
  { label: 'toArray', detail: 'public <T> T[] toArray(T[] a)', documentation: 'Returns array containing all elements in collection.', insertText: 'toArray()', kind: 'Method' },

  // Map methods
  { label: 'put', detail: 'public V put(K key, V value)', documentation: 'Associates specified value with specified key.', insertText: 'put(${1:key}, ${2:value})', kind: 'Method' },
  { label: 'getOrDefault', detail: 'public V getOrDefault(Object key, V defaultValue)', documentation: 'Returns value to which key is mapped, or defaultValue.', insertText: 'getOrDefault(${1:key}, ${2:defaultValue})', kind: 'Method' },
  { label: 'containsKey', detail: 'public boolean containsKey(Object key)', documentation: 'Returns true if map contains mapping for key.', insertText: 'containsKey(${1:key})', kind: 'Method' },
  { label: 'containsValue', detail: 'public boolean containsValue(Object value)', documentation: 'Returns true if map maps one or more keys to value.', insertText: 'containsValue(${1:value})', kind: 'Method' },
  { label: 'keySet', detail: 'public Set<K> keySet()', documentation: 'Returns a Set view of keys contained in map.', insertText: 'keySet()', kind: 'Method' },
  { label: 'values', detail: 'public Collection<V> values()', documentation: 'Returns a Collection view of values contained in map.', insertText: 'values()', kind: 'Method' },
  { label: 'entrySet', detail: 'public Set<Map.Entry<K,V>> entrySet()', documentation: 'Returns a Set view of mappings contained in map.', insertText: 'entrySet()', kind: 'Method' },

  // Queue & Deque
  { label: 'poll', detail: 'public E poll()', documentation: 'Retrieves and removes head of queue, or returns null if empty.', insertText: 'poll()', kind: 'Method' },
  { label: 'peek', detail: 'public E peek()', documentation: 'Retrieves, but does not remove, head of queue.', insertText: 'peek()', kind: 'Method' },
  { label: 'offer', detail: 'public boolean offer(E e)', documentation: 'Inserts specified element into queue.', insertText: 'offer(${1:e})', kind: 'Method' },

  // System, Math, Arrays
  { label: 'System.out.println', detail: 'System.out.println(String x)', documentation: 'Prints a line to standard output.', insertText: 'System.out.println(${1:x});', kind: 'Method' },
  { label: 'System.out.print', detail: 'System.out.print(String x)', documentation: 'Prints to standard output without newline.', insertText: 'System.out.print(${1:x});', kind: 'Method' },
  { label: 'Math.max', detail: 'Math.max(a, b)', documentation: 'Returns greater of two values.', insertText: 'Math.max(${1:a}, ${2:b})', kind: 'Function' },
  { label: 'Math.min', detail: 'Math.min(a, b)', documentation: 'Returns smaller of two values.', insertText: 'Math.min(${1:a}, ${2:b})', kind: 'Function' },
  { label: 'Math.abs', detail: 'Math.abs(a)', documentation: 'Returns absolute value.', insertText: 'Math.abs(${1:a})', kind: 'Function' },
  { label: 'Math.sqrt', detail: 'Math.sqrt(a)', documentation: 'Returns square root of a value.', insertText: 'Math.sqrt(${1:a})', kind: 'Function' },
  { label: 'Math.pow', detail: 'Math.pow(a, b)', documentation: 'Returns value of first argument raised to power of second argument.', insertText: 'Math.pow(${1:a}, ${2:b})', kind: 'Function' },
  { label: 'Arrays.sort', detail: 'Arrays.sort(a)', documentation: 'Sorts the specified array into ascending numerical order.', insertText: 'Arrays.sort(${1:a});', kind: 'Function' },
  { label: 'Arrays.toString', detail: 'Arrays.toString(a)', documentation: 'Returns string representation of contents of specified array.', insertText: 'Arrays.toString(${1:a})', kind: 'Function' },
  { label: 'Collections.sort', detail: 'Collections.sort(list)', documentation: 'Sorts specified list into ascending order.', insertText: 'Collections.sort(${1:list});', kind: 'Function' },
  { label: 'Integer.parseInt', detail: 'Integer.parseInt(s)', documentation: 'Parses string argument as signed decimal integer.', insertText: 'Integer.parseInt(${1:s})', kind: 'Function' },
]

const CPP_COMPLETIONS: CompletionDef[] = [
  // std::vector / container methods
  { label: 'push_back', detail: 'void push_back(const T& value)', documentation: 'Appends given element value to end of container.', insertText: 'push_back(${1:value})', kind: 'Method' },
  { label: 'pop_back', detail: 'void pop_back()', documentation: 'Removes the last element of container.', insertText: 'pop_back()', kind: 'Method' },
  { label: 'emplace_back', detail: 'void emplace_back(Args&&... args)', documentation: 'Appends new element to end of container in-place.', insertText: 'emplace_back(${1:args})', kind: 'Method' },
  { label: 'size', detail: 'size_type size() const', documentation: 'Returns number of elements in container.', insertText: 'size()', kind: 'Method' },
  { label: 'empty', detail: 'bool empty() const', documentation: 'Checks whether container is empty.', insertText: 'empty()', kind: 'Method' },
  { label: 'clear', detail: 'void clear()', documentation: 'Erases all elements from container.', insertText: 'clear()', kind: 'Method' },
  { label: 'resize', detail: 'void resize(size_type count)', documentation: 'Resizes container to contain count elements.', insertText: 'resize(${1:count})', kind: 'Method' },
  { label: 'front', detail: 'reference front()', documentation: 'Returns reference to first element.', insertText: 'front()', kind: 'Method' },
  { label: 'back', detail: 'reference back()', documentation: 'Returns reference to last element.', insertText: 'back()', kind: 'Method' },
  { label: 'at', detail: 'reference at(size_type pos)', documentation: 'Returns reference to element with bounds checking.', insertText: 'at(${1:pos})', kind: 'Method' },
  { label: 'begin', detail: 'iterator begin()', documentation: 'Returns iterator to beginning.', insertText: 'begin()', kind: 'Method' },
  { label: 'end', detail: 'iterator end()', documentation: 'Returns iterator to end.', insertText: 'end()', kind: 'Method' },
  { label: 'rbegin', detail: 'reverse_iterator rbegin()', documentation: 'Returns reverse iterator to beginning.', insertText: 'rbegin()', kind: 'Method' },
  { label: 'rend', detail: 'reverse_iterator rend()', documentation: 'Returns reverse iterator to end.', insertText: 'rend()', kind: 'Method' },
  { label: 'insert', detail: 'iterator insert(const_iterator pos, const T& value)', documentation: 'Inserts elements at specified location in container.', insertText: 'insert(${1:pos}, ${2:value})', kind: 'Method' },
  { label: 'erase', detail: 'iterator erase(const_iterator pos)', documentation: 'Erases specified elements from container.', insertText: 'erase(${1:pos})', kind: 'Method' },

  // std::string methods
  { label: 'length', detail: 'size_type length() const', documentation: 'Returns number of characters in string.', insertText: 'length()', kind: 'Method' },
  { label: 'substr', detail: 'string substr(size_type pos = 0, size_type count = npos) const', documentation: 'Returns substring [pos, pos+count).', insertText: 'substr(${1:pos}, ${2:count})', kind: 'Method' },
  { label: 'find', detail: 'size_type find(const string& str, size_type pos = 0) const', documentation: 'Finds first occurrence of substring.', insertText: 'find(${1:str})', kind: 'Method' },
  { label: 'rfind', detail: 'size_type rfind(const string& str, size_type pos = npos) const', documentation: 'Finds last occurrence of substring.', insertText: 'rfind(${1:str})', kind: 'Method' },
  { label: 'c_str', detail: 'const CharT* c_str() const', documentation: 'Returns pointer to null-terminated character array.', insertText: 'c_str()', kind: 'Method' },

  // std::queue / stack / priority_queue
  { label: 'top', detail: 'reference top()', documentation: 'Accesses top element of stack or priority queue.', insertText: 'top()', kind: 'Method' },
  { label: 'push', detail: 'void push(const T& value)', documentation: 'Pushes element into stack, queue, or priority queue.', insertText: 'push(${1:value})', kind: 'Method' },
  { label: 'pop', detail: 'void pop()', documentation: 'Removes top/front element.', insertText: 'pop()', kind: 'Method' },

  // std::map / set
  { label: 'count', detail: 'size_type count(const Key& key) const', documentation: 'Returns number of elements matching specific key.', insertText: 'count(${1:key})', kind: 'Method' },

  // Algorithms
  { label: 'std::sort', detail: 'std::sort(first, last)', documentation: 'Sorts elements in range [first, last) in ascending order.', insertText: 'std::sort(${1:begin}, ${2:end});', kind: 'Function' },
  { label: 'std::reverse', detail: 'std::reverse(first, last)', documentation: 'Reverses order of elements in range [first, last).', insertText: 'std::reverse(${1:begin}, ${2:end});', kind: 'Function' },
  { label: 'std::max', detail: 'std::max(a, b)', documentation: 'Returns greater of a and b.', insertText: 'std::max(${1:a}, ${2:b})', kind: 'Function' },
  { label: 'std::min', detail: 'std::min(a, b)', documentation: 'Returns smaller of a and b.', insertText: 'std::min(${1:a}, ${2:b})', kind: 'Function' },
  { label: 'std::cout', detail: 'std::cout << val << std::endl;', documentation: 'Standard character output stream.', insertText: 'std::cout << ${1:val} << std::endl;', kind: 'Snippet' },
  { label: 'std::cin', detail: 'std::cin >> var;', documentation: 'Standard character input stream.', insertText: 'std::cin >> ${1:var};', kind: 'Snippet' },
]

const C_COMPLETIONS: CompletionDef[] = [
  { label: 'printf', detail: 'int printf(const char *format, ...)', documentation: 'Prints formatted output to stdout.', insertText: 'printf("${1:%d\\n}", ${2:val});', kind: 'Function' },
  { label: 'scanf', detail: 'int scanf(const char *format, ...)', documentation: 'Reads formatted input from stdin.', insertText: 'scanf("${1:%d}", &${2:var});', kind: 'Function' },
  { label: 'malloc', detail: 'void* malloc(size_t size)', documentation: 'Allocates size bytes of uninitialized storage.', insertText: 'malloc(${1:size})', kind: 'Function' },
  { label: 'calloc', detail: 'void* calloc(size_t num, size_t size)', documentation: 'Allocates memory for array and initializes to zero.', insertText: 'calloc(${1:num}, ${2:size})', kind: 'Function' },
  { label: 'free', detail: 'void free(void *ptr)', documentation: 'Deallocates space previously allocated by malloc/calloc.', insertText: 'free(${1:ptr});', kind: 'Function' },
  { label: 'sizeof', detail: 'sizeof(type)', documentation: 'Queries size of object or type.', insertText: 'sizeof(${1:type})', kind: 'Keyword' },
  { label: 'strlen', detail: 'size_t strlen(const char *str)', documentation: 'Returns length of null-terminated byte string.', insertText: 'strlen(${1:str})', kind: 'Function' },
  { label: 'strcpy', detail: 'char* strcpy(char *dest, const char *src)', documentation: 'Copies character string pointed to by src to dest.', insertText: 'strcpy(${1:dest}, ${2:src});', kind: 'Function' },
  { label: 'strcmp', detail: 'int strcmp(const char *lhs, const char *rhs)', documentation: 'Compares two null-terminated byte strings lexicographically.', insertText: 'strcmp(${1:s1}, ${2:s2})', kind: 'Function' },
  { label: 'memset', detail: 'void* memset(void *dest, int ch, size_t count)', documentation: 'Copies character ch into each of first count characters of dest.', insertText: 'memset(${1:dest}, ${2:0}, ${3:sizeof(dest)});', kind: 'Function' },
  { label: 'memcpy', detail: 'void* memcpy(void *dest, const void *src, size_t count)', documentation: 'Copies count characters from src to dest.', insertText: 'memcpy(${1:dest}, ${2:src}, ${3:count});', kind: 'Function' },
  { label: 'qsort', detail: 'void qsort(void *ptr, size_t count, size_t size, int (*comp)(const void *, const void *))', documentation: 'Sorts array of count elements in place.', insertText: 'qsort(${1:base}, ${2:count}, ${3:sizeof(${1:base}[0])}, ${4:compare});', kind: 'Function' },
]

function getMonacoKind(monaco: any, kind?: string) {
  switch (kind) {
    case 'Method':
      return monaco.languages.CompletionItemKind.Method
    case 'Function':
      return monaco.languages.CompletionItemKind.Function
    case 'Property':
      return monaco.languages.CompletionItemKind.Property
    case 'Class':
      return monaco.languages.CompletionItemKind.Class
    case 'Keyword':
      return monaco.languages.CompletionItemKind.Keyword
    case 'Snippet':
      return monaco.languages.CompletionItemKind.Snippet
    default:
      return monaco.languages.CompletionItemKind.Method
  }
}

export function registerCodeForgeCompletions(monaco: any) {
  if (isRegistered || !monaco || !monaco.languages) return
  isRegistered = true

  const registerForLang = (lang: string, defs: CompletionDef[]) => {
    monaco.languages.registerCompletionItemProvider(lang, {
      triggerCharacters: ['.', '>', ':', '('],
      provideCompletionItems: (model: any, position: any) => {
        const word = model.getWordUntilPosition(position)
        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn,
        }

        const suggestions = defs.map((d) => ({
          label: d.label,
          kind: getMonacoKind(monaco, d.kind),
          detail: d.detail,
          documentation: {
            value: `**${d.detail}**\n\n${d.documentation}`,
          },
          insertText: d.insertText,
          insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
          range,
        }))

        return { suggestions }
      },
    })
  }

  registerForLang('python', PYTHON_COMPLETIONS)
  registerForLang('java', JAVA_COMPLETIONS)
  registerForLang('cpp', CPP_COMPLETIONS)
  registerForLang('c', C_COMPLETIONS)
}
