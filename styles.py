import flet as ft

class AppColors:
    PRIMARY = "#007AFF"       # iOS Blue
    BACKGROUND = "#F2F2F7"    # iOS System Gray 6
    SURFACE = "#FFFFFF"       # White
    TEXT_MAIN = "#000000"
    TEXT_SUB = "#8E8E93"
    DOT_ACTIVE = "#007AFF"    # 点字の凸部分
    DOT_INACTIVE = "#E5E5EA"  # 点字の凹部分
    DIVIDER = "#C6C6C8"
    READING_TEXT = "#FF9500"  # 読み仮名用
    HOVER_BG = "#E5F1FF"      # ホバー時の背景色
    ERROR = "#FF3B30"         # エラー用赤

class TextStyles:
    HEADER = ft.TextStyle(size=22, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_MAIN)
    BODY = ft.TextStyle(size=16, color=AppColors.TEXT_MAIN)
    CAPTION = ft.TextStyle(size=12, color=AppColors.TEXT_SUB)
    BUTTON = ft.TextStyle(size=16, weight=ft.FontWeight.W_500, color=AppColors.SURFACE)
    READING = ft.TextStyle(size=10, weight=ft.FontWeight.BOLD, color=AppColors.READING_TEXT)
    PLATE_LABEL = ft.TextStyle(size=14, weight=ft.FontWeight.BOLD, color=AppColors.PRIMARY)

class ComponentStyles:
    CARD_SHADOW = ft.BoxShadow(
        spread_radius=0,
        blur_radius=10,
        color=ft.Colors.with_opacity(0.1, "#000000"),
        offset=ft.Offset(0, 4),
    )
    
    MAIN_BUTTON_STYLE = ft.ButtonStyle(
        color=AppColors.SURFACE,
        bgcolor=AppColors.PRIMARY,
        shape=ft.RoundedRectangleBorder(radius=12),
        elevation=0,
    )
    
    SUB_BUTTON_STYLE = ft.ButtonStyle(
        color=AppColors.PRIMARY,
        bgcolor=ft.Colors.with_opacity(0.1, AppColors.PRIMARY),
        shape=ft.RoundedRectangleBorder(radius=12),
        elevation=0,
    )
