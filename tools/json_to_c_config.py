#!/usr/bin/env python
# vim: tabstop=2 expandtab bs=2 shiftwidth=2 ai cin smarttab

import argparse
import collections
import json
import os
import sys

parser = argparse.ArgumentParser(description='Create C config boilerplate from a JSON config definition')
parser.add_argument('--c_name', required=True, help="base path of generated files")
parser.add_argument('--dest_dir', default=".", help="base path of generated files")
parser.add_argument('json', nargs='+', help="JSON config definition files")

def do(obj, first_file, path, hdr, schema, src_parse, src_emit, src_free):
  level = len(path) - 1
  indent = '  ' * level
  json_indent = '  ' * (level + 1)
  # path is e.g. "['sys_conf', 'wifi', 'ap']"
  # name is the last component of it, i.e. current structure name
  name = path[-1]
  # Start structure definition
  if level > 0:
    hdr.append(indent + 'struct ' + '_'.join(path) + ' {')
  first_key = True
  for k, v in obj.iteritems():
    key = '.'.join(path[1:] + [k])
    comma = ',' if (not first_key) or (level == 0 and not first_file) else ''
    if isinstance(v, dict):
      jt = 'CONF_TYPE_OBJECT'
      if len(path) > 1:
        ps = '%s.' % '.'.join(path[1:])
      else:
        ps = ''
      # Nested structure
      src_emit.append(
          r'  sj_conf_emit_str(&out, "{comma}\n{indent}\"", "{k}", "\": {{");'
              .format(comma=comma, indent=json_indent, k=k)
      );
      i = len(schema)
      schema.append(None)
      do(v, first_file, path + [k], hdr, schema, src_parse, src_emit, src_free)
      schema[i] = tuple([jt, k, '.num_desc = %d' % (len(schema) - i - 1)])
      src_emit.append(
          r'  sj_conf_emit_str(&out, "\n{indent}", "}}", "");'
              .format(indent=json_indent)
      );
    else:
      c_type = ('char *' if isinstance(v, basestring) else 'int ')
      if isinstance(v, basestring):
        jt = 'CONF_TYPE_STRING'
        getter = 'sj_conf_get_str'
      elif isinstance(v, bool):
        jt = 'CONF_TYPE_BOOL'
        getter = 'sj_conf_get_bool'
      else:
        jt = 'CONF_TYPE_INT'
        getter = 'sj_conf_get_int'

      if len(path) > 1:
        ps = '%s.' % '.'.join(path[1:])
      else:
        ps = ''
      schema.append(tuple([jt, k, '.offset = offsetof(struct %s, %s%s)' % (path[0], ps, k)]))

      # Add "  int foo;" line to the header - goes inside structure definition
      hdr.append(indent + '  ' + c_type + k + ';')

      # Add statements to parse ...
      src_parse.append(
          r'  if ({getter}(toks, "{key}", acl, &cfg->{key}) == 0 && require_keys) goto done;'
          .format(getter=getter, key=key));
      # ... emit ...
      src_emit.append('')
      prefix = comma + r'\n' + json_indent
      if isinstance(v, bool):
        src_emit.append(
            r'''
  sj_conf_emit_str(&out, "{p}\"", "{k}",
                   (cfg->{key} ? "\": true" : "\": false"));'''
                .format(p=prefix, k=k, key=key)
        );
      else:
        src_emit.append(
            r'  sj_conf_emit_str(&out, "{p}\"", "{k}", "\": ");'
                .format(p=prefix, k=k)
        );
        if isinstance(v, basestring):
          src_emit.append(
              r'  sj_conf_emit_str(&out, "\"", cfg->{key}, "\"");'
                  .format(key=key)
          );
        else:
          src_emit.append(
              r'''  sj_conf_emit_int(&out, cfg->{key});'''.format(key=key)
          );
      # ... and free functions.
      if isinstance(v, basestring):
        src_free.append(r'  free(cfg->{key});'.format(key=key));

    first_key = False

  if level > 0:
    hdr.append(indent + '} %s;' % name)

if __name__ == '__main__':
  args = parser.parse_args()
  origin = ' '.join(args.json)
  hdr = []
  src_parse, src_emit, src_free = [], [], []
  name = os.path.basename(args.c_name)

  schema = []
  first_file = True
  for json_file in args.json:
    if os.path.isdir(json_file):
      continue
    with open(json_file) as jf:
      obj = json.load(jf, object_pairs_hook=collections.OrderedDict)
      do(obj, first_file, [name], hdr, schema, src_parse, src_emit, src_free)
    first_file = False
  schema.insert(0, tuple(['CONF_TYPE_OBJECT', '', '.num_desc = %d' % len(schema)]))

  hdr.insert(0, '''/* generated from {origin} - do not edit */
#ifndef _{name_uc}_H_
#define _{name_uc}_H_

struct {name} {{\
'''.format(name=name, name_uc=name.upper(), origin=origin))
  hdr.append('''\
}};

int parse_{name}(const char *json, const char *acl, int require_keys,
                 struct {name} *cfg);
char *emit_{name}(const struct {name} *cfg, const struct {name} *base);
void free_{name}(struct {name} *cfg);

#endif /* _{name_uc}_H_ */
'''.format(name=name, name_uc=name.upper()))
  open(os.path.join(args.dest_dir, name + '.h'), 'w+').write('\n'.join(hdr))

  with open(os.path.join(args.dest_dir, name + '.c'), 'w') as sf:
      sf.write('''\
/* generated from {origin} - do not edit */

#include <stddef.h>
#include "fw/src/sj_config.h"
#include "{name}.h"

struct sj_conf_entry {name}_schema[{num_entries}] = {{
{schema}
}};

int parse_{name}(const char *json, const char *acl, int require_keys,
                 struct {name} *cfg) {{
  return sj_conf_parse(json, acl, require_keys, {name}_schema, cfg);
}}

char *emit_{name}(const struct {name} *cfg, const struct {name} *base) {{
  return sj_conf_emit(cfg, base, {name}_schema);
}}

void free_{name}(struct {name} *cfg) {{
  sj_conf_free({name}_schema, cfg);
}}
'''.format(origin=origin, name=name,
           schema='\n'.join('  {.type = %s, .key = "%s", %s},' % i for i in schema),
           num_entries=len(schema)))
