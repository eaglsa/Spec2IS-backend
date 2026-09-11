import os, re, sys, argparse

def get_core_is_number(raw_is):
    m = re.match(r'^(IS\s+\d+)', raw_is.strip())
    return m.group(1) if m else raw_is.strip()

def extract_part(raw_is, part_col):
    if part_col and part_col.strip():
        return part_col.strip()
    m = re.search(r'\(Part\s*(\d+)\)', raw_is)
    if m:
        return m.group(1)
    return None

def clean_val(val):
    if not val:
        return None
    v = val.strip()
    if v in ('', 'Not identified', 'Not verified in this pass', 'Not publicly available'):
        return None
    return v

def esc(text):
    if text is None:
        return 'NULL'
    clean = str(text).replace(chr(39), chr(39)+chr(39))
    return chr(39) + clean + chr(39)

def parse_markdown_line(line):
    line = line.rstrip()
    if not line.startswith('|') or not line.endswith('|'):
        return None
    content = line[1:-1].replace(chr(92)+'|', '__PIPE__')
    return [p.replace('__PIPE__', '|').strip() for p in content.split('|')]

def parse_txt_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    header_idx = -1
    for i, line in enumerate(lines):
        if '| is_number |' in line:
            header_idx = i
            break
    if header_idx == -1:
        raise ValueError('Header not found')
    headers = [c.strip() for c in lines[header_idx].split('|')[1:-1]]
    rows = []
    for line in lines[header_idx+2:]:
        if line.strip().startswith('|'):
            parts = parse_markdown_line(line)
            if parts and len(parts) == len(headers):
                rows.append(dict(zip(headers, parts)))
    return rows

def generate_sql(rows):
    sqls = ['-- Spec2IS Seed SQL: Indian Standards Metadata & Provenance (Faithful to TXT)', 'BEGIN;']
    
    # 1. Domains
    domains = sorted(list(set(clean_val(r['domain']) for r in rows if clean_val(r['domain']))))
    sqls.append(chr(10) + '-- 1. Standard Domains (Fire Safety, etc.)')
    for d in domains:
        sqls.append('INSERT INTO standard_domains (name) VALUES (' + esc(d) + ') ON CONFLICT (name) DO NOTHING;')

    # 2. Keywords
    keywords = set()
    for r in rows:
        if r['keywords']:
            for k in r['keywords'].split(';'):
                if k.strip():
                    keywords.add(k.strip())
    sqls.append(chr(10) + '-- 2. Standard Searchable Keywords')
    for k in sorted(list(keywords)):
        sqls.append('INSERT INTO standard_keywords (keyword) VALUES (' + esc(k) + ') ON CONFLICT (keyword) DO NOTHING;')

    # 3. Core Standards
    sqls.append(chr(10) + '-- 3. Standards (Core Identity)')
    seen = {}
    for r in rows:
        c = get_core_is_number(r['is_number'])
        if c not in seen:
            seen[c] = r
    for c, r in sorted(seen.items()):
        ec = c.replace(chr(39), chr(39)+chr(39))
        et = esc(r['title'].strip())
        ed = clean_val(r['domain'])
        des = esc(clean_val(r['description']))
        com = esc(clean_val(r['committee_designation']))
        vs = esc(clean_val(r['verification_status']))
        d_sub = '(SELECT id FROM standard_domains WHERE name = ' + esc(ed) + ')' if ed else 'NULL'
        sqls.append('INSERT INTO standards (standard_number, title, domain_id, description, committee_designation, verification_status) VALUES (' + chr(39) + ec + chr(39) + ', ' + et + ', ' + d_sub + ', ' + des + ', ' + com + ', ' + vs + ') ON CONFLICT (standard_number) DO UPDATE SET title = EXCLUDED.title, updated_at = CURRENT_TIMESTAMP;')

    # 4. Keyword Map
    sqls.append(chr(10) + '-- 4. Standard Keywords Mapping')
    for r in rows:
        c = get_core_is_number(r['is_number'])
        if r['keywords']:
            for k in r['keywords'].split(';'):
                if k.strip():
                    ek = k.strip()
                    sqls.append('INSERT INTO standard_keyword_map (standard_id, keyword_id) SELECT s.id, k.id FROM standards s, standard_keywords k WHERE s.standard_number = ' + chr(39) + c + chr(39) + ' AND k.keyword = ' + esc(ek) + ' ON CONFLICT DO NOTHING;')

    # 5. Standard Versions
    sqls.append(chr(10) + '-- 5. Standard Versions (Year/Edition/Status Specific Metadata)')
    for r in rows:
        c = get_core_is_number(r['is_number'])
        yr = int(r['year'].strip())
        ed = esc(clean_val(r['edition']))
        st = esc(clean_val(r['status']))
        vs = esc(clean_val(r['verification_status']))
        nt = esc(r['notes'].strip() if r['notes'] else None)
        sqls.append('INSERT INTO standard_versions (standard_id, year, edition, status, verification_status, notes) SELECT id, ' + str(yr) + ', ' + ed + ', ' + st + ', ' + vs + ', ' + nt + ' FROM standards WHERE standard_number = ' + chr(39) + c + chr(39) + ' ON CONFLICT (standard_id, year) DO UPDATE SET edition = EXCLUDED.edition, status = EXCLUDED.status, verification_status = EXCLUDED.verification_status, notes = EXCLUDED.notes, updated_at = CURRENT_TIMESTAMP;')

    # 6. Standard Parts
    sqls.append(chr(10) + '-- 6. Standard Parts')
    for r in rows:
        p_no = extract_part(r['is_number'], r['part_number'])
        if p_no:
            c = get_core_is_number(r['is_number'])
            yr = int(r['year'].strip())
            pt = esc(r['title'].strip())
            nt = esc(r['notes'].strip() if r['notes'] else None)
            sqls.append('INSERT INTO standard_parts (standard_version_id, part_number, part_title, notes) SELECT v.id, ' + chr(39) + p_no + chr(39) + ', ' + pt + ', ' + nt + ' FROM standard_versions v JOIN standards s ON v.standard_id = s.id WHERE s.standard_number = ' + chr(39) + c + chr(39) + ' AND v.year = ' + str(yr) + ' ON CONFLICT (standard_version_id, part_number) DO UPDATE SET part_title = EXCLUDED.part_title, updated_at = CURRENT_TIMESTAMP;')

    # 7. Standard Sources (Provenance Information for the Metadata)
    sqls.append(chr(10) + '-- 7. Standard Sources & Provenance (Where metadata was obtained/verified)')
    for r in rows:
        c = get_core_is_number(r['is_number'])
        yr = int(r['year'].strip())
        s_raw = r['source'].strip()
        vs = esc(clean_val(r['verification_status']))
        urls = re.findall(r'https?://[^\s;]+', s_raw)
        u_v = esc(urls[0]) if urls else 'NULL'
        s_name = esc(s_raw.split(';')[0].strip())
        prov_text = esc(s_raw) # Complete original provenance text
        s_notes = esc(r['notes'].strip() if 'conflict' in r['notes'].lower() else None)
        
        # Determine source_type based on provenance text
        s_type = 'BIS Portal / Notification' if 'bis' in s_raw.lower() else ('Repository Mirror' if 'resource.org' in s_raw.lower() or 'archive.org' in s_raw.lower() else 'Public Record')
        s_type_v = esc(s_type)

        sqls.append('INSERT INTO standard_sources (standard_id, standard_version_id, source_name, source_url, source_type, provenance_text, verification_status, notes) SELECT s.id, v.id, ' + s_name + ', ' + u_v + ', ' + s_type_v + ', ' + prov_text + ', ' + vs + ', ' + s_notes + ' FROM standards s JOIN standard_versions v ON v.standard_id = s.id WHERE s.standard_number = ' + chr(39) + c + chr(39) + ' AND v.year = ' + str(yr) + ' ON CONFLICT (standard_version_id, source_name) DO UPDATE SET source_url = EXCLUDED.source_url, provenance_text = EXCLUDED.provenance_text, verification_status = EXCLUDED.verification_status, notes = EXCLUDED.notes, updated_at = CURRENT_TIMESTAMP;')

    # 8. Standard Relationships
    sqls.append(chr(10) + '-- 8. Standard Relationships (Revises / Supersedes / Related To)')
    for r in rows:
        rel_text = r['related_standards'].strip()
        if not rel_text:
            continue
        src_std = get_core_is_number(r['is_number'])
        src_yr = int(r['year'].strip())
        rels_to_add = []
        if 'revises ' in rel_text.lower():
            m = re.search(r'revises\s+(IS\s+\d+)(?::(\d{4}))?', rel_text, re.I)
            if m:
                rels_to_add.append((m.group(1), int(m.group(2)) if m.group(2) else None, 'REVISES', rel_text))
            m_sup = re.search(r'superseded\s+(IS\s+\d+)', rel_text, re.I)
            if m_sup:
                rels_to_add.append((m_sup.group(1), None, 'SUPERSEDES', 'Referenced in: ' + rel_text))
        elif 'revised by ' in rel_text.lower():
            m = re.search(r'revised by\s+(IS\s+\d+)(?::(\d{4}))?', rel_text, re.I)
            if m:
                rels_to_add.append((m.group(1), int(m.group(2)) if m.group(2) else None, 'REVISED_BY', rel_text))
        elif 'supersedes ' in rel_text.lower():
            m = re.search(r'supersedes\s+(IS\s+\d+)', rel_text, re.I)
            if m:
                rels_to_add.append((m.group(1), None, 'SUPERSEDES', rel_text))
        elif 'later edition' in rel_text.lower():
            m = re.search(r'later edition of\s+(IS\s+\d+)(?::(\d{4}))?', rel_text, re.I)
            if m:
                rels_to_add.append((m.group(1), int(m.group(2)) if m.group(2) else None, 'REVISES', rel_text))
            else:
                m2 = re.search(r'later edition,\s*(IS\s+\d+)(?::(\d{4}))?', rel_text, re.I)
                if m2:
                    rels_to_add.append((m2.group(1), int(m2.group(2)) if m2.group(2) else None, 'REVISED_BY', rel_text))
        else:
            for p in rel_text.split(';'):
                if p.strip():
                    m = re.search(r'(IS\s+\d+)(?::(\d{4}))?', p)
                    if m:
                        rels_to_add.append((m.group(1), int(m.group(2)) if m.group(2) else None, 'RELATED_TO', p.strip()))
        for tgt_std, tgt_yr, r_type, note in rels_to_add:
            nv = esc(note)
            ty_c = 'AND tv.year = ' + str(tgt_yr) if tgt_yr else ''
            sqls.append('INSERT INTO standard_relationships (source_standard_id, source_version_id, target_standard_id, target_version_id, relationship_type, target_standard_number_raw, notes) SELECT ss.id, sv.id, ts.id, tv.id, ' + chr(39) + r_type + chr(39) + ', ' + chr(39) + tgt_std + chr(39) + ', ' + nv + ' FROM standards ss JOIN standard_versions sv ON sv.standard_id = ss.id AND sv.year = ' + str(src_yr) + ' LEFT JOIN standards ts ON ts.standard_number = ' + chr(39) + tgt_std + chr(39) + ' LEFT JOIN standard_versions tv ON tv.standard_id = ts.id ' + ty_c + ' WHERE ss.standard_number = ' + chr(39) + src_std + chr(39) + ' ON CONFLICT (source_version_id, relationship_type, target_standard_number_raw) DO UPDATE SET target_standard_id = EXCLUDED.target_standard_id, target_version_id = EXCLUDED.target_version_id, notes = EXCLUDED.notes, updated_at = CURRENT_TIMESTAMP;')

    # Explicitly document that standard_parameters and standard_embeddings remain empty
    sqls.append(chr(10) + '-- 9. Technical Parameters (standard_parameters)')
    sqls.append('-- Source TXT contains metadata, not granular technical parameters.')
    sqls.append('-- Table schema is ready and intentionally left empty without manufactured data.')

    sqls.append(chr(10) + '-- 10. Vector Embeddings (standard_embeddings)')
    sqls.append('-- Source TXT does not contain embeddings. pgvector schema is prepared')
    sqls.append('-- for future automated vector enrichment.')

    sqls.append(chr(10) + 'COMMIT;')
    return chr(10).join(sqls)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate seed SQL from Indian Standards metadata TXT file')
    parser.add_argument('--input', '-i', default='IS_fire_building_safety_metadata_extracted.txt', help='Path to metadata TXT file')
    parser.add_argument('--output', '-o', default='seed_data.sql', help='Path to output SQL file')
    args = parser.parse_args()

    input_path = args.input
    if not os.path.exists(input_path):
        # Fallback to local user downloads path if available
        fallback = os.path.expanduser(os.path.join('~', 'Downloads', 'IS_fire_building_safety_metadata_extracted.txt'))
        if os.path.exists(fallback):
            input_path = fallback
        else:
            raise FileNotFoundError(f'Metadata TXT file not found at {input_path} or {fallback}')

    print(f'Parsing metadata file: {input_path}')
    rows = parse_txt_file(input_path)
    print('Parsed rows:', len(rows))
    sql_out = generate_sql(rows)
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(sql_out)
    print(f'{args.output} re-generated successfully with {len(sql_out.splitlines())} lines.')
