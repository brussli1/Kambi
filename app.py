import streamlit as st
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import zipfile
import os
import textwrap

# --- 1. SCRAPER & INDIVIDUAL IMAGE GENERATOR ---
def scrape_and_build_image(product_id, client_name, modifier=None, logo_path="logo.png"):
    detail_url = f"https://www.almacendemascotas.com.py/shop-detail?producto={product_id}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(detail_url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract Title
    product_name = None
    for header in soup.find_all(['h1', 'h2', 'h3', 'h4']):
        text = header.text.strip()
        if text and text.upper() not in ["SHOP", "DETALLES DEL PRODUCTO", "INICIO", "CONTACTO"]:
            product_name = text
            break
    if not product_name:
        raise Exception(f"No se pudo encontrar el nombre para el ID {product_id}.")

    # Extract Price
    price_tag = soup.find(lambda tag: tag.name in ['h2', 'h3', 'h4', 'span', 'p'] and tag.text and 'GS ' in tag.text.upper() and len(tag.text) < 20)
    scraped_price_text = price_tag.text.strip() if price_tag else "0"

    # Extract only digits for math
    try:
        numeric_price = int(''.join(filter(str.isdigit, scraped_price_text)))
    except ValueError:
        numeric_price = 0

    # --- APPLY CUSTOM PRICE/DISCOUNT ---
    final_unit_price = numeric_price
    if modifier:
        if "%" in modifier:
            discount = float(modifier.replace("%", "")) / 100
            final_unit_price = numeric_price * (1 - discount)
        else:
            final_unit_price = float(modifier)

    display_price = f"GS {final_unit_price:,.0f}".replace(",", ".")

    # Extract Main Image
    product_img_url = None
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if src and 'icon' not in src.lower() and 'logo' not in src.lower():
            if src.startswith('//'):
                temp_url = "https:" + src
            elif not src.startswith('http'):
                temp_url = "https://www.almacendemascotas.com.py" + (src if src.startswith('/') else '/' + src)
            else:
                temp_url = src

            if 'fotosweb' in temp_url.lower() or '.jpg' in temp_url.lower():
                product_img_url = temp_url
                break
    if not product_img_url:
        raise Exception(f"Imagen no encontrada para el ID {product_id}.")

    # --- BUILD IMAGE ---
    BRAND_ORANGE = "#FF6600"
    DARK_NAVY = "#071b29"
    LIGHT_GREY = "#959eab"
    CANVAS_W, CANVAS_H = 1080, 1350
    canvas = Image.new('RGB', (CANVAS_W, CANVAS_H), color='#ffffff')
    draw = ImageDraw.Draw(canvas)

    try:
        font_title = ImageFont.truetype("Roboto-Bold.ttf", 55)
        font_subtitle = ImageFont.truetype("Roboto-Regular.ttf", 30)
        font_client = ImageFont.truetype("Roboto-Bold.ttf", 45)
        font_price = ImageFont.truetype("Roboto-Bold.ttf", 100)
    except:
        font_title = font_subtitle = font_client = font_price = ImageFont.load_default()

    # Header
    if os.path.exists(logo_path):
        logo = Image.open(logo_path)
        logo.thumbnail((180, 180), Image.Resampling.LANCZOS)
        if logo.mode == 'RGBA':
            canvas.paste(logo, (60, 50), logo)
        else:
            canvas.paste(logo, (60, 50))

    if client_name:
        text_pre = "PRESUPUESTO PARA:"
        client_text = client_name.upper()
        bbox_pre = draw.textbbox((0, 0), text_pre, font=font_subtitle)
        w_pre = bbox_pre[2] - bbox_pre[0]
        bbox_name = draw.textbbox((0, 0), client_text, font=font_client)
        w_name = bbox_name[2] - bbox_name[0]
        draw.text((CANVAS_W - 60 - w_pre, 60), text_pre, font=font_subtitle, fill=LIGHT_GREY)
        draw.text((CANVAS_W - 60 - w_name, 100), client_text, font=font_client, fill=BRAND_ORANGE)

    # Product Image
    img_response = requests.get(product_img_url)
    product_img = Image.open(BytesIO(img_response.content)).convert("RGBA")
    product_img.thumbnail((750, 750), Image.Resampling.LANCZOS)
    img_w, img_h = product_img.size
    img_x = (CANVAS_W - img_w) // 2
    canvas.paste(product_img, (img_x, 220), product_img)

    # Bottom Text
    margin_left = 60
    current_y = 1000
    wrapped_title = textwrap.fill(product_name.upper(), width=35)
    draw.text((margin_left, current_y), wrapped_title, font=font_title, fill=DARK_NAVY)

    bbox_title = draw.textbbox((margin_left, current_y), wrapped_title, font=font_title)
    current_y = bbox_title[3] + 25
    draw.text((margin_left, current_y), display_price, font=font_price, fill=BRAND_ORANGE)
    draw.line((margin_left, 1300, CANVAS_W - margin_left, 1300), fill=BRAND_ORANGE, width=4)

    return canvas, final_unit_price, product_name

# --- 2. SUMMARY PAGE GENERATOR ---
def build_total_image(client_name, cart_items, total_sum, logo_path="logo.png"):
    BRAND_ORANGE = "#FF6600"
    DARK_NAVY = "#071b29"
    LIGHT_GREY = "#959eab"
    CANVAS_W, CANVAS_H = 1080, 1350
    canvas = Image.new('RGB', (CANVAS_W, CANVAS_H), color='#ffffff')
    draw = ImageDraw.Draw(canvas)

    try:
        font_subtitle = ImageFont.truetype("Roboto-Regular.ttf", 30)
        font_client = ImageFont.truetype("Roboto-Bold.ttf", 45)
        font_list_title = ImageFont.truetype("Roboto-Bold.ttf", 35)
        font_list_item = ImageFont.truetype("Roboto-Regular.ttf", 30)
        font_total_label = ImageFont.truetype("Roboto-Bold.ttf", 50)
        font_total_price = ImageFont.truetype("Roboto-Bold.ttf", 90)
    except:
        font_subtitle = font_client = font_list_title = font_list_item = font_total_label = font_total_price = ImageFont.load_default()

    if os.path.exists(logo_path):
        logo = Image.open(logo_path)
        logo.thumbnail((180, 180), Image.Resampling.LANCZOS)
        if logo.mode == 'RGBA':
            canvas.paste(logo, (60, 50), logo)
        else:
            canvas.paste(logo, (60, 50))

    if client_name:
        text_pre = "RESUMEN PARA:"
        client_text = client_name.upper()
        bbox_pre = draw.textbbox((0, 0), text_pre, font=font_subtitle)
        w_pre = bbox_pre[2] - bbox_pre[0]
        bbox_name = draw.textbbox((0, 0), client_text, font=font_client)
        w_name = bbox_name[2] - bbox_name[0]
        draw.text((CANVAS_W - 60 - w_pre, 60), text_pre, font=font_subtitle, fill=LIGHT_GREY)
        draw.text((CANVAS_W - 60 - w_name, 100), client_text, font=font_client, fill=BRAND_ORANGE)

    # Itemized List
    start_y = 300
    margin = 80
    draw.text((margin, start_y), "CANT", font=font_list_title, fill=DARK_NAVY)
    draw.text((margin + 120, start_y), "PRODUCTO", font=font_list_title, fill=DARK_NAVY)
    draw.text((CANVAS_W - margin - 200, start_y), "SUBTOTAL", font=font_list_title, fill=DARK_NAVY)
    draw.line((margin, start_y + 50, CANVAS_W - margin, start_y + 50), fill=LIGHT_GREY, width=2)

    current_y = start_y + 80
    for item in cart_items:
        qty_str = f"{item['qty']}x"
        name_str = item['name'][:32] + "..." if len(item['name']) > 35 else item['name']
        subtotal_str = f"GS {item['subtotal']:,.0f}".replace(",", ".")

        draw.text((margin, current_y), qty_str, font=font_list_item, fill=BRAND_ORANGE)
        draw.text((margin + 120, current_y), name_str, font=font_list_item, fill=DARK_NAVY)

        bbox_sub = draw.textbbox((0, 0), subtotal_str, font=font_list_item)
        w_sub = bbox_sub[2] - bbox_sub[0]
        draw.text((CANVAS_W - margin - w_sub, current_y), subtotal_str, font=font_list_item, fill=DARK_NAVY)
        current_y += 50

    # Grand Total
    total_label = "TOTAL DEL PRESUPUESTO"
    total_formatted = f"GS {total_sum:,.0f}".replace(",", ".")
    bbox_label = draw.textbbox((0, 0), total_label, font=font_total_label)
    draw.text(((CANVAS_W - (bbox_label[2] - bbox_label[0])) // 2, 1050), total_label, font=font_total_label, fill=DARK_NAVY)

    bbox_price = draw.textbbox((0, 0), total_formatted, font=font_total_price)
    draw.text(((CANVAS_W - (bbox_price[2] - bbox_price[0])) // 2, 1130), total_formatted, font=font_total_price, fill=BRAND_ORANGE)
    draw.line((60, 1300, CANVAS_W - 60, 1300), fill=BRAND_ORANGE, width=4)

    return canvas

# --- 3. STREAMLIT UI ---
st.set_page_config(page_title="La Huella - Presupuestos", page_icon="🐾")

st.title("🐾 Generador de Presupuestos")
st.markdown("**La Huella Pet Store**")

# Input Fields
client_name = st.text_input("Nombre del cliente", placeholder="Ej: Veterinaria San Roque")
st.caption("Formato: ID:CANTIDAD:DESCUENTO (Ej: 1420:2, 544:1:10%, 992:3:150000)")
raw_ids = st.text_area("IDs de los productos", placeholder="1420:2, 544:1:10%...")
export_format = st.radio("Formato de exportación", ["PDF (Recomendado)", "JPGs individuales (Archivo ZIP)"])

if st.button("Generar Ofertas", type="primary"):
    if not raw_ids:
        st.error("Por favor ingresa al menos un ID.")
    else:
        generated_images = []
        errors = []
        cart_items = []
        total_sum = 0
        raw_items = [item.strip() for item in raw_ids.split(",") if item.strip()]

        # Show a loading spinner
        with st.spinner('Extrayendo datos de la web y generando imágenes...'):
            for item in raw_items:
                try:
                    parts = item.split(':')
                    pid = parts[0].strip()
                    qty = int(parts[1].strip()) if len(parts) > 1 else 1
                    modifier = parts[2].strip() if len(parts) > 2 else None

                    img, final_unit_price, product_name = scrape_and_build_image(pid, client_name, modifier)

                    subtotal = final_unit_price * qty
                    total_sum += subtotal
                    cart_items.append({'name': product_name, 'qty': qty, 'unit_price': final_unit_price, 'subtotal': subtotal})
                    generated_images.append(img)
                except Exception as e:
                    errors.append(f"Error en {item}: {str(e)}")

            if generated_images and cart_items:
                total_img = build_total_image(client_name, cart_items, total_sum)
                generated_images.append(total_img)

        # Show Results
        if errors:
            for err in errors:
                st.warning(err)

        if not generated_images:
            st.error("No se pudo generar ninguna imagen.")
        else:
            st.success(f"¡Éxito! Se generaron {len(generated_images)} páginas.")

            # Preview the images in the web browser
            with st.expander("Vista Previa de Imágenes", expanded=False):
                for img in generated_images:
                    st.image(img, use_container_width=True)

            # --- DOWNLOAD LOGIC ---
            if export_format == "PDF (Recomendado)":
                pdf_buffer = BytesIO()
                first_image = generated_images[0].convert('RGB')
                if len(generated_images) > 1:
                    rgb_images = [img.convert('RGB') for img in generated_images[1:]]
                    first_image.save(pdf_buffer, format="PDF", resolution=150.0, save_all=True, append_images=rgb_images)
                else:
                    first_image.save(pdf_buffer, format="PDF", resolution=150.0)

                st.download_button(
                    label="📄 Descargar PDF",
                    data=pdf_buffer.getvalue(),
                    file_name="Presupuesto_La_Huella.pdf",
                    mime="application/pdf"
                )

            else:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for i, img in enumerate(generated_images):
                        img_buffer = BytesIO()
                        img.convert('RGB').save(img_buffer, format="JPEG", quality=95)

                        if i == len(generated_images) - 1 and cart_items:
                            filename = "Oferta_RESUMEN.jpg"
                        else:
                            pid = raw_items[i].split(':')[0]
                            filename = f"Oferta_{pid}.jpg"

                        zf.writestr(filename, img_buffer.getvalue())

                st.download_button(
                    label="🗂️ Descargar ZIP con JPGs",
                    data=zip_buffer.getvalue(),
                    file_name="Ofertas_La_Huella.zip",
                    mime="application/zip"
                )
