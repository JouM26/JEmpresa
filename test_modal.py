import flet as ft

def main(page: ft.Page):
    page.title = "Test Modal"
    
    txt = ft.TextField(label="Nombre")
    
    def cerrar_dialog(e):
        dialog.open = False
        page.update()
    
    def abrir_dialog(e):
        print("Abriendo diálogo...")
        page.dialog = dialog
        dialog.open = True
        print(f"dialog.open = {dialog.open}")
        print(f"dialog.modal = {dialog.modal}")
        page.update()
        print("Update completado")
    
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Test"),
        content=txt,
        actions=[
            ft.TextButton("Cerrar", on_click=cerrar_dialog)
        ]
    )
    
    page.add(
        ft.Column([
            ft.Text("Presiona el botón"),
            ft.ElevatedButton("Abrir Modal", on_click=abrir_dialog)
        ])
    )

ft.app(target=main)
