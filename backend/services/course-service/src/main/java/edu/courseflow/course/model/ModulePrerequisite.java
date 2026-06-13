package edu.courseflow.course.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.UUID;

@Entity
@Table(name = "module_prerequisites")
public class ModulePrerequisite {

    @Id
    private UUID id;

    @Column(name = "module_id", nullable = false)
    private UUID moduleId;

    @Column(name = "required_module_id", nullable = false)
    private UUID requiredModuleId;

    @Column(name = "rule_type", nullable = false, length = 60)
    private String ruleType;

    protected ModulePrerequisite() {
    }

    public UUID getModuleId() {
        return moduleId;
    }

    public UUID getRequiredModuleId() {
        return requiredModuleId;
    }

    public String getRuleType() {
        return ruleType;
    }
}
