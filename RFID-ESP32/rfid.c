#include <string.h>
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_http_client.h"
#include "esp_rc522.h"
#include "cJSON.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define SSID      "TU_SSID"
#define PASSWORD  "TU_CONTRASENA"
#define SERVER    "http://192.168.1.100:5000"
#define PIN_CS    5
#define LED_R     25
#define LED_G     26
#define LED_B     27
#define BUZZER    32

static const char *TAG = "RFID_ACC";
static esp_rc522_handle_t scanner;
static char uid_str[20];

// ---- LED y Buzzer ----
static void set_led(bool r, bool g, bool b) {
    gpio_set_level(LED_R, r);
    gpio_set_level(LED_G, g);
    gpio_set_level(LED_B, b);
}
static void beep(uint32_t ms) {
    gpio_set_level(BUZZER, 1);
    vTaskDelay(pdMS_TO_TICKS(ms));
    gpio_set_level(BUZZER, 0);
}

// ---- Verificar acceso via HTTP ----
static bool verificar_acceso(const char *uid) {
    char url[128];
    snprintf(url, sizeof(url), "%s/check?uid=%s", SERVER, uid);
    char buf[256] = {0};
    esp_http_client_config_t cfg = { .url = url,
        .user_data = buf, .buffer_size_tx = 256 };
    esp_http_client_handle_t c = esp_http_client_init(&cfg);
    esp_err_t err = esp_http_client_perform(c);
    esp_http_client_cleanup(c);
    if (err != ESP_OK) return false;
    cJSON *root = cJSON_Parse(buf);
    bool ok = cJSON_IsTrue(cJSON_GetObjectItem(root, "autorizado"));
    cJSON_Delete(root);
    return ok;
}

// ---- Callback RFID ----
static void on_tag_scanned(void *arg, esp_event_base_t base,
                           int32_t id, void *data) {
    if (id != RC522_EVENT_TAG_SCANNED) return;
    esp_rc522_tag_t *tag =
        ((esp_rc522_event_data_t *)data)->ptr;
    snprintf(uid_str, sizeof(uid_str),
             RC522_UID_FMT, RC522_UID_ARG(tag->serial_number));
    ESP_LOGI(TAG, "Tarjeta: %s", uid_str);
    set_led(1, 1, 1);                   // Blanco: procesando
    bool ok = verificar_acceso(uid_str);
    if (ok) {
        ESP_LOGI(TAG, "ACCESO CONCEDIDO");
        set_led(0, 1, 0); beep(150);
    } else {
        ESP_LOGI(TAG, "ACCESO DENEGADO");
        set_led(1, 0, 0); beep(600);
    }
    vTaskDelay(pdMS_TO_TICKS(2500));
    set_led(0, 0, 1);                   // Azul: en espera
}

void app_main(void) {
    // GPIOs
    gpio_config_t io = { .pin_bit_mask =
        (1ULL<<LED_R)|(1ULL<<LED_G)|(1ULL<<LED_B)|(1ULL<<BUZZER),
        .mode = GPIO_MODE_OUTPUT };
    gpio_config(&io);
    set_led(1, 1, 0);                   // Amarillo: conectando

    // Wi-Fi
    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t wcfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&wcfg);
    esp_wifi_set_mode(WIFI_MODE_STA);
    wifi_config_t wsta = { .sta = { .ssid = SSID,
                                    .password = PASSWORD } };
    esp_wifi_set_config(WIFI_IF_STA, &wsta);
    esp_wifi_start();
    esp_wifi_connect();
    vTaskDelay(pdMS_TO_TICKS(3000));    // Esperar conexion
    ESP_LOGI(TAG, "Wi-Fi conectado");
    set_led(0, 0, 1);                   // Azul: listo

    // RFID
    esp_rc522_spi_config_t spi = { .host = SPI2_HOST,
        .miso_gpio=19, .mosi_gpio=23, .sck_gpio=18, .sda_gpio=PIN_CS };
    esp_rc522_config_t rcfg = { .transport = ESP_RC522_TRANSPORT_SPI,
        .transport_config.spi = &spi };
    ESP_ERROR_CHECK(esp_rc522_create(&rcfg, &scanner));
    ESP_ERROR_CHECK(esp_rc522_register_events(scanner,
        RC522_EVENT_ANY, on_tag_scanned, NULL));
    ESP_ERROR_CHECK(esp_rc522_start(scanner));
    ESP_LOGI(TAG, "Sistema listo. Acerque su tarjeta.");
}