package generated;

/** Высшее учебное заведение */
public class University {
    
    /** Факультеты университета */
    private Department departments;
    
    /** Название университета */
    private String name;
    
    /** Год основания */
    private String founding_year;
    

    public University() {
        
        this.departments = null;
        
        this.name = "";
        
        this.founding_year = "";
        
    }

    
    public Department getDepartments() {
        return this.departments;
    }

    public void setDepartments(Department departments) {
        this.departments = departments;
    }
    
    public String getName() {
        return this.name;
    }

    public void setName(String name) {
        this.name = name;
    }
    
    public String getFounding_year() {
        return this.founding_year;
    }

    public void setFounding_year(String founding_year) {
        this.founding_year = founding_year;
    }
    

    @Override
    public String toString() {
        return "University{" +
            
            "departments=" + departments + ", " + 
            "name=" + name + ", " + 
            "founding_year=" + founding_year + "" +
            '}';
    }
}