import struct
import zipfile
import math
from braille_logic import BRAILLE_MAP, NUM_INDICATOR, SPACE_MARK

class STLGenerator:
    def generate_package(self, flat_cells, output_zip_path, max_chars_per_line=10, max_lines_per_plate=1, original_text_str="", base_thickness=1.0):
        """旧メソッド互換用"""
        lines = [flat_cells[i:i + max_chars_per_line] for i in range(0, len(flat_cells), max_chars_per_line)]
        plates = [lines[i:i + max_lines_per_plate] for i in range(0, len(lines), max_lines_per_plate)]
        return self.generate_package_from_plates(plates, output_zip_path, original_text_str, base_thickness)

    def generate_package_from_plates(self, plates_data, output_zip_path, original_text_str="", base_thickness=1.0):
        """
        プレートデータを受け取ってZIP生成
        """
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr("original_text.txt", original_text_str.encode('utf-8'))
            
            # BSE出力
            bse_content = self._generate_bse_content(plates_data)
            zipf.writestr("braille.bse", bse_content.encode('utf-8'))

            pages_info = []
            for i, plate_lines in enumerate(plates_data):
                page_num = i + 1
                page_num_dots = self._int_to_braille_dots(page_num)
                
                plate_body_dots = []
                for line in plate_lines:
                    line_dots = [c['dots'] for c in line]
                    plate_body_dots.append(line_dots)
                
                pages_info.append({
                    'page_num': page_num,
                    'plate_lines': plate_lines, 
                    'page_dots': page_num_dots,
                    'body_lines_dots': plate_body_dots
                })

            html_content = self._generate_guide_html(pages_info)
            zipf.writestr("guide_sheet.html", html_content.encode('utf-8'))

            for info in pages_info:
                stl_filename = f"plate_{info['page_num']:02d}.stl"
                stl_data = self._create_plate_stl(info['body_lines_dots'], info['page_dots'], base_thickness)
                zipf.writestr(stl_filename, stl_data)
        
        return output_zip_path

    def _generate_bse_content(self, plates_data):
        """BSE形式(Braille ASCII)に変換"""
        ascii_map = {
            0x00: ' ', 0x01: 'a', 0x03: 'b', 0x09: 'c', 0x19: 'd', 0x11: 'e',
            0x0B: 'f', 0x1B: 'g', 0x13: 'h', 0x0A: 'i', 0x1A: 'j', 0x05: 'k',
            0x07: 'l', 0x0D: 'm', 0x1D: 'n', 0x15: 'o', 0x0F: 'p', 0x1F: 'q',
            0x17: 'r', 0x0E: 's', 0x1E: 't', 0x25: 'u', 0x27: 'v', 0x3A: 'w',
            0x2D: 'x', 0x3D: 'y', 0x35: 'z',
            0x3C: '#', 0x30: ';', 0x10: '"', 0x20: ',', 0x08: '@', 0x18: '^', 0x28: '_',
            0x02: '1', 0x06: '2', 0x12: '3', 0x32: '4', 0x22: '5', 0x16: '6',
            0x36: '7', 0x26: '8', 0x14: '9', 0x34: '0', 
            0x04: "'", 0x0C: '/', 0x1C: '>', 0x24: '-', 0x2C: '%', 0x3E: '=',
            0x21: '*', 0x23: '<', 0x29: '[', 0x2B: '$', 0x2F: '+', 0x31: ']',
            0x33: ':', 0x37: '?', 0x38: '!', 0x39: '(', 0x3B: ')', 0x3F: '|'
        }

        bse_lines = []
        for plate in plates_data:
            for line_cells in plate:
                line_str = ""
                for cell in line_cells:
                    dots = cell['dots']
                    val = 0
                    if dots[0]: val += 1
                    if dots[1]: val += 2
                    if dots[2]: val += 4
                    if dots[3]: val += 8
                    if dots[4]: val += 16
                    if dots[5]: val += 32
                    line_str += ascii_map.get(val, '?')
                bse_lines.append(line_str)
            bse_lines.append("") 
        return "\r\n".join(bse_lines)

    def _int_to_braille_dots(self, n):
        s = str(n)
        dots = [NUM_INDICATOR]
        for char in s:
             dots.append(BRAILLE_MAP.get(char, SPACE_MARK))
        return dots

    def _create_plate_stl(self, body_lines_dots, page_num_dots, base_thickness=1.0):
        # 寸法 (平坦化対応)
        DOT_BASE_DIA = 1.6
        DOT_HEIGHT = 0.75
        DOT_PITCH_X = 2.2
        DOT_PITCH_Y = 2.4
        CHAR_PITCH = 6.0
        LINE_HEIGHT = 10.0
        LINE_PITCH = 12.0
        BASE_THICKNESS = base_thickness
        
        MARGIN_TOP = 4.0
        MARGIN_BOTTOM = 4.0
        MARGIN_RIGHT = 4.0
        MARGIN_LEFT = 4.0
        
        HOLE_DIA = 5.0
        HOLE_RADIUS = HOLE_DIA / 2
        HOLE_RING_WIDTH = 1.5 
        
        LEFT_SIDE_WIDTH = max(HOLE_DIA + HOLE_RING_WIDTH*2 + 4.0, len(page_num_dots) * CHAR_PITCH)
        if LEFT_SIDE_WIDTH < 15.0: LEFT_SIDE_WIDTH = 15.0

        num_lines = len(body_lines_dots)
        max_line_chars = 0
        for line in body_lines_dots:
            max_line_chars = max(max_line_chars, len(line))
        body_width = max_line_chars * CHAR_PITCH
        
        total_width = MARGIN_LEFT + LEFT_SIDE_WIDTH + body_width + MARGIN_RIGHT
        total_height = MARGIN_TOP + LINE_HEIGHT + ((num_lines - 1) * LINE_PITCH) + MARGIN_BOTTOM
        
        min_height_for_hole = (HOLE_RADIUS + HOLE_RING_WIDTH) * 2 + 4.0
        if total_height < min_height_for_hole:
            total_height = min_height_for_hole

        triangles = []

        hole_cx = MARGIN_LEFT + (HOLE_RADIUS + HOLE_RING_WIDTH)
        hole_cy = total_height - (MARGIN_TOP + HOLE_RADIUS + HOLE_RING_WIDTH)
        
        self._add_plate_with_hole(
            triangles, 
            width=total_width, height=total_height, depth=BASE_THICKNESS, 
            corner_radius=3.0, 
            hole_cx=hole_cx, hole_cy=hole_cy, hole_r=HOLE_RADIUS
        )

        self._add_tube(
            triangles, 
            cx=hole_cx, cy=hole_cy, z_base=BASE_THICKNESS, 
            r_inner=HOLE_RADIUS, r_outer=HOLE_RADIUS + HOLE_RING_WIDTH, 
            height=DOT_HEIGHT
        )

        page_num_y = MARGIN_BOTTOM + LINE_HEIGHT/2 
        page_num_x = MARGIN_LEFT
        page_content_width = len(page_num_dots) * CHAR_PITCH
        if page_content_width < LEFT_SIDE_WIDTH:
            page_num_x += (LEFT_SIDE_WIDTH - page_content_width) / 2
            
        dots_center_y_offset = DOT_PITCH_Y 
        current_x = page_num_x
        pg_y = page_num_y - dots_center_y_offset 

        if len(body_lines_dots) > 1:
            for char_dots in page_num_dots:
                self._add_braille_char(triangles, char_dots, current_x, pg_y, BASE_THICKNESS, DOT_BASE_DIA, DOT_HEIGHT, DOT_PITCH_X, DOT_PITCH_Y)
                current_x += CHAR_PITCH

        body_start_x = MARGIN_LEFT + LEFT_SIDE_WIDTH
        first_line_center_y = total_height - MARGIN_TOP - LINE_HEIGHT/2
        
        for i, line_dots in enumerate(body_lines_dots):
            line_center_y = first_line_center_y - (i * LINE_PITCH)
            line_y = line_center_y - dots_center_y_offset
            
            line_x = body_start_x
            for char_dots in line_dots:
                self._add_braille_char(triangles, char_dots, line_x, line_y, BASE_THICKNESS, DOT_BASE_DIA, DOT_HEIGHT, DOT_PITCH_X, DOT_PITCH_Y)
                line_x += CHAR_PITCH

        header = b'Tenji P-Fab Generated STL' + b'\0' * (80 - 25)
        num_tris = len(triangles)
        
        data = bytearray()
        data.extend(header)
        data.extend(struct.pack('<I', num_tris))
        
        for normal, v1, v2, v3 in triangles:
            data.extend(struct.pack('<3f', 0.0, 0.0, 0.0)) 
            data.extend(struct.pack('<3f', *v1))
            data.extend(struct.pack('<3f', *v2))
            data.extend(struct.pack('<3f', *v3))
            data.extend(struct.pack('<H', 0))
            
        return data

    def _add_plate_with_hole(self, triangles, width, height, depth, corner_radius, hole_cx, hole_cy, hole_r):
        segments = 32
        outer_points = self._generate_rounded_rect_path(width, height, corner_radius, segments)
        hole_points = []
        num_outer = len(outer_points)
        
        for px, py in outer_points:
            vx = px - hole_cx
            vy = py - hole_cy
            dist = math.sqrt(vx*vx + vy*vy)
            if dist == 0: dist = 0.001
            hx = hole_cx + (vx / dist) * hole_r
            hy = hole_cy + (vy / dist) * hole_r
            hole_points.append((hx, hy))
            
        for i in range(num_outer):
            next_i = (i + 1) % num_outer
            o1 = (outer_points[i][0], outer_points[i][1], depth)
            o2 = (outer_points[next_i][0], outer_points[next_i][1], depth)
            i2 = (hole_points[next_i][0], hole_points[next_i][1], depth)
            i1 = (hole_points[i][0], hole_points[i][1], depth)
            triangles.append(((0,0,1), o1, o2, i1))
            triangles.append(((0,0,1), i1, o2, i2))
            o1_b = (outer_points[i][0], outer_points[i][1], 0)
            o2_b = (outer_points[next_i][0], outer_points[next_i][1], 0)
            i2_b = (hole_points[next_i][0], hole_points[next_i][1], 0)
            i1_b = (hole_points[i][0], hole_points[i][1], 0)
            triangles.append(((0,0,-1), o1_b, i1_b, o2_b))
            triangles.append(((0,0,-1), i1_b, i2_b, o2_b))
            triangles.append(((0,0,0), o1_b, o2_b, o2))
            triangles.append(((0,0,0), o1_b, o2, o1))
            triangles.append(((0,0,0), i1_b, i1, i2_b))
            triangles.append(((0,0,0), i2_b, i1, i2))

    def _generate_rounded_rect_path(self, w, h, r, segments_per_corner=8):
        points = []
        cx, cy = w - r, h - r
        for i in range(segments_per_corner + 1):
            ang = 0 + (math.pi/2 * i / segments_per_corner)
            points.append((cx + r*math.cos(ang), cy + r*math.sin(ang)))
        cx, cy = r, h - r
        for i in range(segments_per_corner + 1):
            ang = math.pi/2 + (math.pi/2 * i / segments_per_corner)
            points.append((cx + r*math.cos(ang), cy + r*math.sin(ang)))
        cx, cy = r, r
        for i in range(segments_per_corner + 1):
            ang = math.pi + (math.pi/2 * i / segments_per_corner)
            points.append((cx + r*math.cos(ang), cy + r*math.sin(ang)))
        cx, cy = w - r, r
        for i in range(segments_per_corner + 1):
            ang = 3*math.pi/2 + (math.pi/2 * i / segments_per_corner)
            points.append((cx + r*math.cos(ang), cy + r*math.sin(ang)))
        return points

    def _add_tube(self, triangles, cx, cy, z_base, r_inner, r_outer, height):
        segments = 32
        top_z = z_base + height
        for i in range(segments):
            ang1 = 2 * math.pi * i / segments
            ang2 = 2 * math.pi * (i + 1) / segments
            idx1 = cx + r_inner * math.cos(ang1); idy1 = cy + r_inner * math.sin(ang1)
            idx2 = cx + r_inner * math.cos(ang2); idy2 = cy + r_inner * math.sin(ang2)
            odx1 = cx + r_outer * math.cos(ang1); ody1 = cy + r_outer * math.sin(ang1)
            odx2 = cx + r_outer * math.cos(ang2); ody2 = cy + r_outer * math.sin(ang2)
            p_i1 = (idx1, idy1, top_z); p_i2 = (idx2, idy2, top_z)
            p_o1 = (odx1, ody1, top_z); p_o2 = (odx2, ody2, top_z)
            triangles.append(((0,0,1), p_o1, p_o2, p_i1))
            triangles.append(((0,0,1), p_i1, p_o2, p_i2))
            b_o1 = (odx1, ody1, z_base); b_o2 = (odx2, ody2, z_base)
            triangles.append(((0,0,0), b_o1, b_o2, p_o2))
            triangles.append(((0,0,0), b_o1, p_o2, p_o1))
            b_i1 = (idx1, idy1, z_base); b_i2 = (idx2, idy2, z_base)
            triangles.append(((0,0,0), b_i1, p_i1, b_i2))
            triangles.append(((0,0,0), b_i2, p_i1, p_i2))

    def _add_braille_char(self, triangles, dots, x, y, z_base, dia, height, px, py):
        offsets = [
            (0, 2*py), (0, py), (0, 0),
            (px, 2*py), (px, py), (px, 0)
        ]
        for i, is_on in enumerate(dots):
            if is_on:
                dx, dy = offsets[i]
                cx = x + dx + dia/2
                cy = y + dy + dia/2
                self._add_dot_mesh(triangles, cx, cy, z_base, dia/2, height)

    def _add_dot_mesh(self, triangles, cx, cy, cz, r, h):
        segments = 24
        rings = 6
        flat_ratio = 0.5
        theta_limit = (math.pi / 2) * flat_ratio
        sin_limit = math.sin(theta_limit)
        z_scale = 1.0 / sin_limit
        
        prev_ring_points = []
        
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            bx = cx + r * math.cos(angle)
            by = cy + r * math.sin(angle)
            prev_ring_points.append((bx, by, cz))
            
        for j in range(1, rings + 1):
            theta = theta_limit * (j / rings)
            z_curr = cz + (h * math.sin(theta)) * z_scale
            if j == rings:
                z_curr = cz + h
            r_curr = r * math.cos(theta)
            current_ring_points = []
            
            if j == rings: 
                top_center = (cx, cy, z_curr)
                for i in range(segments):
                    angle = 2 * math.pi * i / segments
                    rx = cx + r_curr * math.cos(angle)
                    ry = cy + r_curr * math.sin(angle)
                    current_ring_points.append((rx, ry, z_curr))
                
                for i in range(segments):
                    next_i = (i + 1) % segments
                    p1_lower = prev_ring_points[i]
                    p2_lower = prev_ring_points[next_i]
                    p1_upper = current_ring_points[i]
                    p2_upper = current_ring_points[next_i]
                    triangles.append(((0,0,1), p1_lower, p2_lower, p1_upper))
                    triangles.append(((0,0,1), p1_upper, p2_lower, p2_upper))
                
                for i in range(segments):
                    p1 = current_ring_points[i]
                    p2 = current_ring_points[(i + 1) % segments]
                    triangles.append(((0,0,1), p1, p2, top_center))
                    
            else:
                for i in range(segments):
                    angle = 2 * math.pi * i / segments
                    rx = cx + r_curr * math.cos(angle)
                    ry = cy + r_curr * math.sin(angle)
                    current_ring_points.append((rx, ry, z_curr))
                
                for i in range(segments):
                    next_i = (i + 1) % segments
                    p1_lower = prev_ring_points[i]
                    p2_lower = prev_ring_points[next_i]
                    p1_upper = current_ring_points[i]
                    p2_upper = current_ring_points[next_i]
                    triangles.append(((0,0,1), p1_lower, p2_lower, p1_upper))
                    triangles.append(((0,0,1), p1_upper, p2_lower, p2_upper))
                
                prev_ring_points = current_ring_points

    def _generate_guide_html(self, pages_info):
        rows = ""
        for info in pages_info:
            page_num = info['page_num']
            plate_lines = info['plate_lines']
            page_dots = info['page_dots']
            page_braille_str = "".join([self._dots_to_unicode(d) for d in page_dots])

            rows += f"<div class='plate-block'><h2>Plate {page_num:02d} <span class='page-braille'>({page_braille_str})</span></h2>"
            rows += "<table border='1' cellspacing='0' cellpadding='5' style='border-collapse: collapse; width: 100%;'>"
            rows += "<tr style='background-color: #f0f0f0;'><th>Line</th><th>Content</th></tr>"
            
            for line_idx, line_cells in enumerate(plate_lines):
                line_content_html = ""
                for cell in line_cells:
                    char = cell['char']
                    uni_char = self._dots_to_unicode(cell['dots'])
                    line_content_html += f"<div style='display:inline-block; text-align:center; margin:2px; border:1px solid #eee; padding:2px;'><div style='font-size:20px;'>{uni_char}</div><div style='font-size:12px;'>{char}</div></div>"
                
                rows += f"<tr><td align='center' width='50'>L{line_idx+1}</td><td>{line_content_html}</td></tr>"
            rows += "</table></div><br>"

        return f"""
        <html><head><meta charset="UTF-8">
        <style>
            body {{ font-family: "Noto Sans JP", sans-serif; padding: 20px; color: #333; }}
            h2 {{ border-bottom: 2px solid #007AFF; margin-top: 30px; }}
            .page-braille {{ font-size: 1.5em; color: #555; vertical-align: middle; }}
            .plate-block {{ page-break-inside: avoid; margin-bottom: 40px; }}
            table {{ width: 100%; border: 1px solid #ddd; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
        </style>
        </head><body>
            <h1>Tenji P-Fab Export Guide</h1>
            {rows}
        </body></html>
        """

    def _dots_to_unicode(self, dots):
        code = 0x2800
        if dots[0]: code += 0x01
        if dots[1]: code += 0x02
        if dots[2]: code += 0x04
        if dots[3]: code += 0x08
        if dots[4]: code += 0x10
        if dots[5]: code += 0x20
        return chr(code)
