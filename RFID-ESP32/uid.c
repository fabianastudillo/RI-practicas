#include "esp_log.h"
#include "esp_rc522.h"

#define PIN_MISO 19
#define PIN_MOSI 23
#define PIN_SCLK 18
#define PIN_CS    5

static const char *TAG = "RFID";
static esp_rc522_handle_t scanner;

static void on_tag_scanned(void *arg, esp_event_base_t base,
                           int32_t id, void *data)
{
    esp_rc522_event_data_t *ev = (esp_rc522_event_data_t *)data;
    if (id == RC522_EVENT_TAG_SCANNED) {
        esp_rc522_tag_t *tag = (esp_rc522_tag_t *)ev->ptr;
        ESP_LOGI(TAG, "UID: " RC522_UID_FMT,
                 RC522_UID_ARG(tag->serial_number));
    }
}

void app_main(void)
{
    esp_rc522_spi_config_t spi = {
        .host      = SPI2_HOST,
        .miso_gpio = PIN_MISO,
        .mosi_gpio = PIN_MOSI,
        .sck_gpio  = PIN_SCLK,
        .sda_gpio  = PIN_CS,
    };
    esp_rc522_config_t cfg = { .transport = ESP_RC522_TRANSPORT_SPI,
                                .transport_config.spi = &spi };

    ESP_ERROR_CHECK(esp_rc522_create(&cfg, &scanner));
    ESP_ERROR_CHECK(esp_rc522_register_events(scanner,
                    RC522_EVENT_ANY, on_tag_scanned, NULL));
    ESP_ERROR_CHECK(esp_rc522_start(scanner));
    ESP_LOGI(TAG, "Acerque una tarjeta RFID...");
}