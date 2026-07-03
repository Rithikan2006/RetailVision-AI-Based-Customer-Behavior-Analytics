import cv2
import numpy as np
import os
from database import get_recent_movements

def generate_heatmap(output_filename="heatmap.png"):
    width, height = 1280, 720
    bg = np.ones((height, width, 3), dtype=np.uint8) * 35
    
    zones = {
        'Entrance': (0, 500, 250, 720),
        'Vegetables': (100, 100, 450, 400),
        'Snacks': (550, 100, 900, 400),
        'Beverages': (950, 100, 1280, 500),
        'Billing': (950, 500, 1280, 720)
    }
    
    for name, coords in zones.items():
        x1, y1, x2, y2 = coords
        cv2.rectangle(bg, (x1, y1), (x2, y2), (70, 70, 70), 2)
        cv2.putText(bg, name, (x1 + 10, y1 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (120, 120, 120), 1, cv2.LINE_AA)
        
    cv2.rectangle(bg, (400, 100), (500, 600), (50, 50, 50), -1)
    cv2.rectangle(bg, (400, 100), (500, 600), (90, 90, 90), 1)
    cv2.putText(bg, "Shelf A", (415, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

    cv2.rectangle(bg, (750, 100), (850, 600), (50, 50, 50), -1)
    cv2.rectangle(bg, (750, 100), (850, 600), (90, 90, 90), 1)
    cv2.putText(bg, "Shelf B", (765, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

    movements = get_recent_movements(limit=10000)
    accum_map = np.zeros((height, width), dtype=np.float32)
    
    if movements:
        for move in movements:
            x, y = move['x'], move['y']
            if 0 <= x < width and 0 <= y < height:
                cv2.circle(accum_map, (x, y), 25, 1.0, -1)
        
        accum_map = cv2.GaussianBlur(accum_map, (51, 51), 0)
        max_val = accum_map.max()
        if max_val > 0:
            accum_map = (accum_map / max_val * 255).astype(np.uint8)
        else:
            accum_map = accum_map.astype(np.uint8)
            
        color_heatmap = cv2.applyColorMap(accum_map, cv2.COLORMAP_JET)
        threshold = 15
        _, mask = cv2.threshold(accum_map, threshold, 255, cv2.THRESH_BINARY)
        mask_inv = cv2.bitwise_not(mask)
        
        heatmap_fg = cv2.bitwise_and(color_heatmap, color_heatmap, mask=mask)
        bg_bg = cv2.bitwise_and(bg, bg, mask=mask_inv)
        bg_fg = cv2.bitwise_and(bg, bg, mask=mask)
        blended_heatmap_semi = cv2.addWeighted(heatmap_fg, 0.7, bg_fg, 0.3, 0)
        final_heatmap = cv2.add(bg_bg, blended_heatmap_semi)
    else:
        final_heatmap = bg
        cv2.putText(final_heatmap, "No movement data found. Start tracking first!", 
                    (300, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    os.makedirs(static_dir, exist_ok=True)
    heatmaps_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'heatmaps')
    os.makedirs(heatmaps_dir, exist_ok=True)
    
    cv2.imwrite(os.path.join(static_dir, output_filename), final_heatmap)
    cv2.imwrite(os.path.join(heatmaps_dir, output_filename), final_heatmap)
    print(f"Heatmap saved to static/{output_filename} and heatmaps/{output_filename}")
    return final_heatmap

if __name__ == '__main__':
    generate_heatmap()