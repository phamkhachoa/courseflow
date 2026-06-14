package edu.courseflow.promotion.contract;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.networknt.schema.JsonSchema;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SpecVersion;
import com.networknt.schema.ValidationMessage;
import edu.courseflow.events.common.EventMetadata;
import edu.courseflow.events.incentive.IncentiveEffectPayload;
import edu.courseflow.events.incentive.IncentiveRedemptionCommittedEvent;
import edu.courseflow.events.incentive.IncentiveRedemptionReversedEvent;
import edu.courseflow.promotion.dto.PromotionDtos.AuditEventDto;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignVersionDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportApprovalResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportCommitResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunListItemDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunQueryResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunIssueDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunRowDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportIssueExportDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportOperationDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportOperationQueryResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveReconciliationEffectDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveReconciliationEntryDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveReconciliationQueryResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionExecutionResponseDto;
import java.io.IOException;
import java.io.Reader;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.StreamSupport;
import org.junit.jupiter.api.Test;
import org.yaml.snakeyaml.Yaml;

class IncentiveContractPackTest {

    private static final Pattern MAPPING = Pattern.compile(
            "@(?:Get|Post|Patch|Delete)Mapping\\((?:value\\s*=\\s*)?\"([^\"]+)\"");
    private static final ObjectMapper JSON = new ObjectMapper()
            .findAndRegisterModules()
            .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);

    @Test
    void openApiCoversEveryPromotionControllerRoute() throws Exception {
        Map<String, Object> openApi = yaml(contractRoot().resolve("openapi.yaml"));
        @SuppressWarnings("unchecked")
        Map<String, Object> paths = (Map<String, Object>) openApi.get("paths");

        assertThat(paths).isNotEmpty();
        assertThat(paths.keySet()).containsAll(controllerRoutes());
    }

    @Test
    void openApiComponentReferencesResolveToDeclaredSchemas() throws Exception {
        Map<String, Object> openApi = yaml(contractRoot().resolve("openapi.yaml"));
        Set<String> referencedSchemas = new LinkedHashSet<>();
        collectComponentSchemaRefs(openApi, referencedSchemas);

        assertThat(openApiSchemas(openApi).keySet()).containsAll(referencedSchemas);
    }

    @Test
    void openApiSchemasCoverSerializedRuntimeDtos() throws Exception {
        Map<String, Object> openApi = yaml(contractRoot().resolve("openapi.yaml"));
        Instant now = Instant.parse("2026-06-14T00:00:00Z");
        UUID campaignId = UUID.fromString("11111111-1111-1111-1111-111111111111");

        assertOpenApiSchemaCoversSerializedFields(openApi, "CampaignVersion",
                new CampaignVersionDto(
                        UUID.fromString("22222222-2222-2222-2222-222222222222"),
                        campaignId,
                        3,
                        "PUBLISHED",
                        true,
                        "author-1",
                        "author-1",
                        "reviewer-1",
                        "publisher-1",
                        "approved",
                        now,
                        now,
                        now,
                        now));
        assertRequired(openApiSchema(openApi, "CampaignVersion"), "versionStatus");
        assertThat(requiredFields(openApiSchema(openApi, "CampaignVersion"))).doesNotContain("status");

        assertOpenApiSchemaCoversSerializedFields(openApi, "Coupon",
                new CouponDto(
                        UUID.fromString("33333333-3333-3333-3333-333333333333"),
                        campaignId,
                        "WEL***10",
                        null,
                        "WEL***10",
                        "ACTIVE",
                        null,
                        now,
                        now,
                        1,
                        1,
                        Map.of("channel", "web"),
                        now,
                        now));

        assertOpenApiSchemaCoversSerializedFields(openApi, "CouponImportDryRunResponse",
                new CouponImportDryRunResponseDto(
                        UUID.fromString("77777777-7777-7777-7777-777777777777"),
                        campaignId,
                        true,
                        2,
                        1,
                        1,
                        1,
                        0,
                        true,
                        false,
                        "sha256:dry-run-result",
                        now,
                        List.of("SAMPLE_ROWS_TRUNCATED"),
                        List.of(new CouponImportDryRunIssueDto(
                                3,
                                "SA****10",
                                "code",
                                "DUPLICATE_IN_FILE",
                                "Coupon code is duplicated in the CSV file")),
                        List.of(new CouponImportDryRunRowDto(
                                2,
                                "SA****10",
                                "VALID",
                                List.of()))));

        assertOpenApiSchemaCoversSerializedFields(openApi, "CouponImportCommitResponse",
                new CouponImportCommitResponseDto(
                        UUID.fromString("88888888-8888-8888-8888-888888888888"),
                        UUID.fromString("99999999-9999-9999-9999-999999999999"),
                        UUID.fromString("77777777-7777-7777-7777-777777777777"),
                        campaignId,
                        "SUCCEEDED",
                        2,
                        2,
                        "hmac-sha256:test:commit-result",
                        false,
                        now,
                        List.of()));

        assertOpenApiSchemaCoversSerializedFields(openApi, "CouponImportApprovalResponse",
                new CouponImportApprovalResponseDto(
                        UUID.fromString("99999999-9999-9999-9999-999999999999"),
                        "PENDING_APPROVAL",
                        UUID.fromString("77777777-7777-7777-7777-777777777777"),
                        campaignId,
                        "hmac-sha256:test:result",
                        2,
                        2,
                        0,
                        0,
                        0,
                        true,
                        true,
                        "launch",
                        "CHG-100",
                        "maker-1",
                        null,
                        null,
                        null,
                        now.plusSeconds(3600),
                        now,
                        null,
                        null,
                        null));

        assertOpenApiSchemaCoversSerializedFields(openApi, "CouponImportDryRunQueryResponse",
                new CouponImportDryRunQueryResponseDto(
                        List.of(new CouponImportDryRunListItemDto(
                                UUID.fromString("77777777-7777-7777-7777-777777777777"),
                                "tenant-a",
                                "learn",
                                campaignId,
                                "COMPLETED",
                                2,
                                2,
                                0,
                                0,
                                0,
                                true,
                                true,
                                "hmac-sha256:test:result",
                                "maker-1",
                                "corr-1",
                                "admin-web",
                                now,
                                now.plusSeconds(3600),
                                null,
                                null,
                                null,
                                0,
                                null)),
                        50,
                        false,
                        now));
        assertOpenApiSchemaCoversSerializedFields(openApi, "CouponImportDryRunListItem",
                new CouponImportDryRunListItemDto(
                        UUID.fromString("77777777-7777-7777-7777-777777777777"),
                        "tenant-a",
                        "learn",
                        campaignId,
                        "COMPLETED",
                        2,
                        2,
                        0,
                        0,
                        0,
                        true,
                        true,
                        "hmac-sha256:test:result",
                        "maker-1",
                        "corr-1",
                        "admin-web",
                        now,
                        now.plusSeconds(3600),
                        null,
                        null,
                        null,
                        0,
                        null));

        assertOpenApiSchemaCoversSerializedFields(openApi, "CouponImportIssueExport",
                new CouponImportIssueExportDto(
                        UUID.fromString("77777777-7777-7777-7777-777777777777"),
                        campaignId,
                        "tenant-a",
                        "learn",
                        "INVALID",
                        1,
                        "coupon-import-77777777-7777-7777-7777-777777777777-invalid.csv",
                        "text/csv",
                        "rowNumber,codeMask,rowStatus,issueCodes\r\n2,SA****10,INVALID,DUPLICATE_IN_FILE\r\n",
                        now));

        assertOpenApiSchemaCoversSerializedFields(openApi, "CouponImportOperationQueryResponse",
                new CouponImportOperationQueryResponseDto(
                        List.of(new CouponImportOperationDto(
                                UUID.fromString("88888888-8888-8888-8888-888888888888"),
                                UUID.fromString("99999999-9999-9999-9999-999999999999"),
                                UUID.fromString("77777777-7777-7777-7777-777777777777"),
                                "tenant-a",
                                "learn",
                                campaignId,
                                "SUCCEEDED",
                                2,
                                2,
                                "hmac-sha256:test:commit-result",
                                "launch",
                                "CHG-100",
                                "committer-1",
                                "corr-commit",
                                "admin-web",
                                now)),
                        50,
                        false,
                        now));
        assertOpenApiSchemaCoversSerializedFields(openApi, "CouponImportOperation",
                new CouponImportOperationDto(
                        UUID.fromString("88888888-8888-8888-8888-888888888888"),
                        UUID.fromString("99999999-9999-9999-9999-999999999999"),
                        UUID.fromString("77777777-7777-7777-7777-777777777777"),
                        "tenant-a",
                        "learn",
                        campaignId,
                        "SUCCEEDED",
                        2,
                        2,
                        "hmac-sha256:test:commit-result",
                        "launch",
                        "CHG-100",
                        "committer-1",
                        "corr-commit",
                        "admin-web",
                        now));

        assertOpenApiSchemaCoversSerializedFields(openApi, "AuditEvent",
                new AuditEventDto(
                        UUID.fromString("44444444-4444-4444-4444-444444444444"),
                        "tenant-a",
                        "learn",
                        campaignId.toString(),
                        "CAMPAIGN",
                        "PUBLISH",
                        "reviewer-1",
                        "ok",
                        Map.of("version", 3),
                        null,
                        null,
                        now));

        assertOpenApiSchemaCoversSerializedFields(openApi, "IncentiveReconciliationQueryResponse",
                new IncentiveReconciliationQueryResponseDto(
                        List.of(new IncentiveReconciliationEntryDto(
                                UUID.fromString("abababab-abab-abab-abab-abababababab"),
                                "redemption-1:COMMIT:effect-1",
                                "MATCHED",
                                List.of(),
                                "APPLY",
                                "COMMIT",
                                UUID.fromString("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                                UUID.fromString("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                                "tenant-a",
                                "learn",
                                campaignId,
                                3,
                                UUID.fromString("cccccccc-cccc-cccc-cccc-cccccccccccc"),
                                "profile-1",
                                "order-1",
                                "REDEEMED",
                                "NO_QUOTA_CHANGE",
                                null,
                                "PUBLISHED",
                                "incentive.redemption.committed",
                                now,
                                "corr-1",
                                "checkout-service",
                                now,
                                now,
                                null,
                                new IncentiveReconciliationEffectDto(
                                        "effect-1",
                                        "ORDER_FIXED_OFF",
                                        "DISCOUNT",
                                        "ORDER_FIXED_OFF",
                                        "ORDER",
                                        null,
                                        BigDecimal.TEN,
                                        "USD",
                                        "MONEY",
                                        BigDecimal.TEN,
                                        3,
                                        Map.of("campaignId", campaignId.toString())))),
                        50,
                        false,
                        now));

        assertOpenApiSchemaCoversSerializedFields(openApi, "RetentionExecutionResponse",
                new RetentionExecutionResponseDto(
                        UUID.fromString("55555555-5555-5555-5555-555555555555"),
                        "EXECUTED",
                        "promotion-redemption-retention",
                        "v1",
                        "promotion_redemptions",
                        null,
                        null,
                        now,
                        UUID.fromString("66666666-6666-6666-6666-666666666666"),
                        "sha256:result",
                        10,
                        10,
                        100,
                        false,
                        false,
                        now));

        JsonNode executionRequest = openApiSchema(openApi, "RetentionExecutionRequest");
        assertRequired(executionRequest, "approvalId", "idempotencyKey", "confirm");
        assertThat(requiredFields(executionRequest))
                .doesNotContain("policyId", "approvedDryRunId", "approvedResultHash");
        assertThat(executionRequest.at("/properties/confirm/const").asBoolean()).isTrue();
    }

    @Test
    void asyncApiDeclaresRedemptionEventTopics() throws Exception {
        Map<String, Object> asyncApi = yaml(contractRoot().resolve("asyncapi.yaml"));
        @SuppressWarnings("unchecked")
        Map<String, Object> channels = (Map<String, Object>) asyncApi.get("channels");

        assertThat(channels.keySet())
                .contains("incentive.redemption.committed", "incentive.redemption.reversed");
    }

    @Test
    void eventSchemasKeepPortableReconciliationFields() throws Exception {
        JsonNode committed = jsonSchema("incentive-redemption-committed.v1.json");
        JsonNode reversed = jsonSchema("incentive-redemption-reversed.v1.json");
        JsonNode reconciliation = jsonSchema("incentive-reconciliation-entry.v1.json");

        assertRequired(committed, "eventId", "schemaVersion", "tenantId", "applicationId",
                "reservationId", "redemptionId", "campaignId", "campaignVersion", "profileId",
                "correlationId", "sourceClientId", "effects", "committedAt");
        assertThat(committed.at("/properties/couponId/type").toString()).contains("null");
        assertNullableProperty(committed, "correlationId");
        assertNullableProperty(committed, "sourceClientId");

        assertRequired(reversed, "eventId", "schemaVersion", "tenantId", "applicationId",
                "reservationId", "redemptionId", "campaignId", "campaignVersion", "profileId",
                "correlationId", "sourceClientId", "reason", "quotaReleased", "effects", "reversedAt");
        assertThat(reversed.at("/properties/quotaReleased/type").asText()).isEqualTo("boolean");
        assertNullableProperty(reversed, "correlationId");
        assertNullableProperty(reversed, "sourceClientId");

        assertRequired(reconciliation, "schemaVersion", "operationType", "operationId",
                "reservationId", "redemptionId", "campaignId", "campaignVersion", "effectId",
                "benefitType", "actionType", "amount", "currency", "unit", "quantity", "direction",
                "occurredAt", "correlationId", "sourceClientId");
        assertNullableProperty(reconciliation, "correlationId");
        assertNullableProperty(reconciliation, "sourceClientId");
    }

    @Test
    void eventSchemasAcceptRuntimeNullableInternalMetadata() throws Exception {
        Instant now = Instant.parse("2026-06-14T00:00:00Z");
        IncentiveEffectPayload effect = new IncentiveEffectPayload(
                "effect-1",
                "ORDER_PERCENT_OFF",
                "DISCOUNT",
                "ORDER_PERCENT_OFF",
                "ORDER",
                null,
                BigDecimal.TEN,
                "USD",
                "MONEY",
                BigDecimal.TEN,
                1,
                Map.of("campaignVersion", 1));
        IncentiveRedemptionCommittedEvent committed = new IncentiveRedemptionCommittedEvent(
                "evt-commit-1",
                1,
                "tenant-a",
                "learn",
                UUID.fromString("77777777-7777-7777-7777-777777777777").toString(),
                UUID.fromString("88888888-8888-8888-8888-888888888888").toString(),
                UUID.fromString("99999999-9999-9999-9999-999999999999").toString(),
                1,
                null,
                "profile-1",
                "checkout-1",
                null,
                null,
                List.of(effect),
                now,
                new EventMetadata(null, null, "actor-1", Map.of()));
        IncentiveRedemptionReversedEvent reversed = new IncentiveRedemptionReversedEvent(
                "evt-reverse-1",
                1,
                committed.tenantId(),
                committed.applicationId(),
                committed.reservationId(),
                committed.redemptionId(),
                committed.campaignId(),
                committed.campaignVersion(),
                null,
                committed.profileId(),
                committed.externalReference(),
                null,
                null,
                "CUSTOMER_REFUND",
                false,
                List.of(effect),
                now,
                new EventMetadata(null, null, "actor-1", Map.of()));

        assertThat(serializedMap(committed))
                .containsEntry("correlationId", null)
                .containsEntry("sourceClientId", null);
        assertThat(serializedMap(reversed))
                .containsEntry("correlationId", null)
                .containsEntry("sourceClientId", null);
        assertValidAgainstSchema(eventSchemaWithInlinedEffect("incentive-redemption-committed.v1.json"),
                JSON.valueToTree(committed));
        assertValidAgainstSchema(eventSchemaWithInlinedEffect("incentive-redemption-reversed.v1.json"),
                JSON.valueToTree(reversed));
        assertNullableProperty(jsonSchema("incentive-redemption-committed.v1.json"), "correlationId");
        assertNullableProperty(jsonSchema("incentive-redemption-committed.v1.json"), "sourceClientId");
        assertNullableProperty(jsonSchema("incentive-redemption-reversed.v1.json"), "correlationId");
        assertNullableProperty(jsonSchema("incentive-redemption-reversed.v1.json"), "sourceClientId");
    }

    @Test
    void examplesAreJsonAndDoNotExposeStoredCouponSecrets() throws Exception {
        Path examples = contractRoot().resolve("examples");
        try (var files = Files.list(examples)) {
            files.filter(path -> path.toString().endsWith(".json"))
                    .forEach(this::assertSafeExample);
        }
    }

    @Test
    void goldenExamplesContainRequiredSchemaFields() throws Exception {
        JsonNode effect = jsonSchema("incentive-effect.v1.json");
        JsonNode committed = jsonSchema("incentive-redemption-committed.v1.json");
        JsonNode reversed = jsonSchema("incentive-redemption-reversed.v1.json");
        JsonNode reconciliation = jsonSchema("incentive-reconciliation-entry.v1.json");

        JsonNode committedExample = jsonExample("incentive-redemption-committed.json");
        JsonNode reversedExample = jsonExample("incentive-redemption-reversed.json");
        assertRequiredFieldsPresent(committed, committedExample);
        assertRequiredFieldsPresent(reversed, reversedExample);
        assertRequiredFieldsPresent(effect, committedExample.get("effects").get(0));
        assertRequiredFieldsPresent(effect, reversedExample.get("effects").get(0));
        assertValidAgainstSchema(eventSchemaWithInlinedEffect("incentive-redemption-committed.v1.json"),
                committedExample);
        assertValidAgainstSchema(eventSchemaWithInlinedEffect("incentive-redemption-reversed.v1.json"),
                reversedExample);
        assertValidAgainstSchema(effect, committedExample.get("effects").get(0));
        assertValidAgainstSchema(effect, reversedExample.get("effects").get(0));

        JsonNode reconciliationCommitExample = jsonExample("incentive-reconciliation-commit.json");
        JsonNode reconciliationReverseExample = jsonExample("incentive-reconciliation-reverse.json");
        assertRequiredFieldsPresent(reconciliation, reconciliationCommitExample);
        assertRequiredFieldsPresent(reconciliation, reconciliationReverseExample);
        assertValidAgainstSchema(reconciliation, reconciliationCommitExample);
        assertValidAgainstSchema(reconciliation, reconciliationReverseExample);
    }

    @Test
    void compatibilityDocumentFreezesReconciliationAndLoyaltyBoundaries() throws Exception {
        String compatibility = Files.readString(contractRoot().resolve("compatibility.md"));

        assertThat(compatibility)
                .contains("redemptionId + effectId")
                .contains("COMMIT")
                .contains("REVERSE")
                .contains("POINTS_EARN_INTENT")
                .contains("must not own loyalty balances");
    }

    private void assertSafeExample(Path path) {
        try {
            JsonNode payload = JSON.readTree(path.toFile());
            String text = payload.toString();
            assertThat(text)
                    .doesNotContain("normalizedCode")
                    .doesNotContain("couponFingerprint")
                    .doesNotContain("fingerprint")
                    .doesNotContain("WELCOME10")
                    .doesNotContain("rawSnapshot");
        } catch (IOException ex) {
            throw new AssertionError("Invalid JSON example: " + path, ex);
        }
    }

    private JsonNode jsonSchema(String filename) throws IOException {
        return JSON.readTree(contractRoot().resolve("schemas").resolve(filename).toFile());
    }

    private JsonNode jsonExample(String filename) throws IOException {
        return JSON.readTree(contractRoot().resolve("examples").resolve(filename).toFile());
    }

    private JsonNode eventSchemaWithInlinedEffect(String filename) throws IOException {
        ObjectNode schema = (ObjectNode) jsonSchema(filename).deepCopy();
        ObjectNode effects = (ObjectNode) schema.path("properties").path("effects");
        effects.set("items", jsonSchema("incentive-effect.v1.json"));
        return schema;
    }

    private void assertRequired(JsonNode schema, String... fields) {
        assertThat(requiredFields(schema)).contains(fields);
    }

    private List<String> requiredFields(JsonNode schema) {
        List<String> required = StreamSupport.stream(schema.get("required").spliterator(), false)
                .map(JsonNode::asText)
                .toList();
        return required;
    }

    private void assertRequiredFieldsPresent(JsonNode schema, JsonNode example) {
        List<String> required = StreamSupport.stream(schema.get("required").spliterator(), false)
                .map(JsonNode::asText)
                .toList();
        assertThat(example).isNotNull();
        for (String field : required) {
            assertThat(example.has(field))
                    .as("required field %s missing in example %s", field, example)
                    .isTrue();
        }
    }

    private void assertNullableProperty(JsonNode schema, String property) {
        JsonNode type = schema.path("properties").path(property).path("type");
        assertThat(type.isArray())
                .as("schema property %s should use an explicit nullable type array", property)
                .isTrue();
        List<String> types = StreamSupport.stream(type.spliterator(), false)
                .map(JsonNode::asText)
                .toList();
        assertThat(types).contains("null");
    }

    private void assertOpenApiSchemaCoversSerializedFields(Map<String, Object> openApi,
                                                           String schemaName,
                                                           Object dto) {
        assertThat(schemaPropertyNames(openApi, schemaName))
                .as("OpenAPI schema %s should cover serialized fields for %s", schemaName, dto.getClass().getName())
                .containsAll(serializedMap(dto).keySet());
    }

    private void assertValidAgainstSchema(JsonNode schemaNode, JsonNode payload) {
        JsonSchema schema = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012).getSchema(schemaNode);
        Set<ValidationMessage> errors = schema.validate(payload);
        assertThat(errors)
                .as("JSON payload should conform to schema. Payload: %s", payload)
                .isEmpty();
    }

    private Set<String> schemaPropertyNames(Map<String, Object> openApi, String schemaName) {
        @SuppressWarnings("unchecked")
        Map<String, Object> schema = (Map<String, Object>) openApiSchemas(openApi).get(schemaName);
        assertThat(schema).as("OpenAPI schema %s exists", schemaName).isNotNull();
        @SuppressWarnings("unchecked")
        Map<String, Object> properties = (Map<String, Object>) schema.get("properties");
        assertThat(properties).as("OpenAPI schema %s has properties", schemaName).isNotNull();
        return properties.keySet();
    }

    private JsonNode openApiSchema(Map<String, Object> openApi, String schemaName) {
        return JSON.valueToTree(openApiSchemas(openApi).get(schemaName));
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> openApiSchemas(Map<String, Object> openApi) {
        Map<String, Object> components = (Map<String, Object>) openApi.get("components");
        return (Map<String, Object>) components.get("schemas");
    }

    private void collectComponentSchemaRefs(Object node, Set<String> refs) {
        if (node instanceof Map<?, ?> map) {
            Object ref = map.get("$ref");
            if (ref instanceof String text && text.startsWith("#/components/schemas/")) {
                refs.add(text.substring("#/components/schemas/".length()));
            }
            map.values().forEach(value -> collectComponentSchemaRefs(value, refs));
            return;
        }
        if (node instanceof Iterable<?> values) {
            values.forEach(value -> collectComponentSchemaRefs(value, refs));
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> serializedMap(Object value) {
        return JSON.convertValue(value, Map.class);
    }

    private Set<String> controllerRoutes() throws IOException {
        String source = Files.readString(controllerPath());
        Matcher matcher = MAPPING.matcher(source);
        Set<String> routes = new LinkedHashSet<>();
        while (matcher.find()) {
            routes.add("/internal/incentives" + matcher.group(1));
        }
        assertThat(routes).isNotEmpty();
        return routes;
    }

    private Map<String, Object> yaml(Path path) throws IOException {
        Yaml yaml = new Yaml();
        try (Reader reader = Files.newBufferedReader(path)) {
            return yaml.load(reader);
        }
    }

    private Path contractRoot() {
        return findExisting("backend/docs/contracts/incentives", "docs/contracts/incentives");
    }

    private Path controllerPath() {
        return findExisting(
                "backend/services/promotion-service/src/main/java/edu/courseflow/promotion/controller/PromotionController.java",
                "src/main/java/edu/courseflow/promotion/controller/PromotionController.java");
    }

    private Path findExisting(String repoRelative, String moduleRelative) {
        Path cwd = Path.of("").toAbsolutePath();
        for (Path path = cwd; path != null; path = path.getParent()) {
            Path repoCandidate = path.resolve(repoRelative).normalize();
            if (Files.exists(repoCandidate)) {
                return repoCandidate;
            }
            Path moduleCandidate = path.resolve(moduleRelative).normalize();
            if (Files.exists(moduleCandidate)) {
                return moduleCandidate;
            }
        }
        throw new IllegalStateException("Could not locate " + repoRelative + " or " + moduleRelative);
    }
}
