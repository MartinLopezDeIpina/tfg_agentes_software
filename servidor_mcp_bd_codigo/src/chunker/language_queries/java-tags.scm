(class_declaration
  name: (identifier) @name.definition.class) @definition.class

(method_declaration
  name: (identifier) @name.definition.method) @definition.function

(method_invocation
  name: (identifier) @name.reference.call
  arguments: (argument_list) @reference.call)